"""Check shipped controllers using the engine's copied playback-variable table.

This models the two disassembled speed-evaluator call sites: the final variable
is replaced with clip duration. It does not execute the graphics engine.
"""
from pathlib import Path
import collections, hashlib, json, math, struct as S, sys, zipfile
from project_env import PROJECT, CHECKS, HCM

CONTROLLERS = PROJECT / 'tools'
sys.path.insert(0, str(CONTROLLERS))
from inspect_controllers import Reader, ASSETS
from build_variable_resources import transform, RESERVED_DURATION_HASH, VARIABLE, STOP
from build_resource_patches import raw_records, h

SOURCE = PROJECT / 'src/HavocConditionPacks/native-melee'
manifest = json.loads((SOURCE / 'manifest.json').read_text())
mapping = json.loads((CONTROLLERS / 'melee-state-map.json').read_text())
targets = collections.defaultdict(set)
for row in mapping['targets']:
    targets[row['asset']].add((row['layer'], row['index']))


def array(data, parsed, name, code):
    a = parsed[name]
    return list(S.unpack_from('<' + code * a['count'], data, a['data']))


def speed(state, unit_values, clip_duration):
    # Unit.animation_get_variable reads unit_values, whereas playback reads
    # this temporary table. Inspecting only Unit values misses the old bug.
    copied = list(unit_values)
    copied[-1] = clip_duration
    offset = state['fields'][0]
    word = state['words'][offset]
    assert state['words'][offset + 1] == STOP
    if word & 0xfff00000 == VARIABLE:
        return copied[word & 0xfffff]
    return S.unpack('<f', S.pack('<I', word))[0]


shipped, copies = {}, 0
for patch in manifest['patches']:
    path = SOURCE / 'resources' / patch['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == patch['sha256']
    _, rows = raw_records(path)
    for row in rows:
        key = f'{row["name"]:016x}'
        assert row['ext'] == h('state_machine') and key in targets
        data = row['body']
        if key in shipped:
            assert shipped[key] == data, ('inconsistent duplicate', key)
        shipped[key] = data
        copies += 1
assert len(manifest['patches']) == 54 and copies == 78
assert set(shipped) == set(targets) and len(shipped) == 21

checks, expected_legacy_failures, crusher = 0, 0, []
durations = (.125, .5, 1.0, 2.5, 4.5, 5.333333, 9.0)
for key, data in shipped.items():
    original = (ASSETS / (key + '.state_machine')).read_bytes()
    before, after = Reader(original).read(), Reader(data).read()
    expected, variables, changes = transform(original, targets[key])
    # transform also undoes every authorized edit and verifies byte-exact
    # restoration, covering transitions, blend times, movement and other states.
    assert data == expected
    names = array(data, after, 'names', 'I')
    old_names = array(original, before, 'names', 'I')
    assert names[-1] == old_names[-1] == RESERVED_DURATION_HASH
    assert names[:len(old_names)-1] == old_names[:-1]
    assert len(set(names)) == len(names)
    base = array(data, after, 'defaults', 'f')
    active = list(base)
    for variable in variables:
        assert variable['index'] < len(base) - 1
        active[variable['index']] *= 1.2
    maximum = max(v['bits'] for v in variables)
    for old, state in zip(before['states'], after['states']):
        pair = state['layer'], state['index']
        if pair not in targets[key]:
            continue
        native = S.unpack('<f', S.pack('<I', old['words'][old['fields'][0]]))[0]
        # Exercise enable -> disable -> re-enable using the same table/state.
        for values, rate in [(base, 1), (active, 1.2), (base, 1), (active, 1.2)]:
            for duration in durations:
                actual = speed(state, values, duration)
                assert math.isclose(actual, native * rate, rel_tol=1e-7), (key, pair, actual, native * rate)
                checks += 1
        if old['words'][old['fields'][0]] == maximum:
            expected_legacy_failures += 1
        if key == '5266d735100376cc':
            crusher.append((state, native, base, active))

# Alternate the Crusher's moving/standing/heavy states on the same controller;
# changing clip duration must never change the configured playback multiplier.
assert len(crusher) > 5
for turn in range(100):
    for i, (state, native, base, active) in enumerate(crusher):
        rate = 1 if turn % 3 == 0 else 1.2
        values = base if rate == 1 else active
        assert math.isclose(speed(state, values, durations[(turn+i) % len(durations)]), native*rate, rel_tol=1e-7)

# Negative control from the immutable released payload, not a hand-built model
# of our builder. The same engine-table assertion must detect the old fault.
legacy_failures = set()
legacy = HCM / 'release/4.4.8/HavocConditionManager-4.4.8.zip'
with zipfile.ZipFile(legacy) as archive:
    import tempfile
    with tempfile.TemporaryDirectory(prefix='legacy-speed-check-', dir=CHECKS) as temporary:
        legacy_manifest = json.loads(archive.read('HavocConditionManager/native-melee/manifest.json'))
        for row in legacy_manifest['patches']:
            path = Path(temporary) / row['file']
            path.write_bytes(archive.read('HavocConditionManager/native-melee/resources/' + row['file']))
            _, records = raw_records(path)
            for record in records:
                key = f'{record["name"]:016x}'
                data = record['body']; parsed = Reader(data).read()
                names = array(data, parsed, 'names', 'I')
                values = array(data, parsed, 'defaults', 'f')
                assert names[-1] != RESERVED_DURATION_HASH
                for state in parsed['states']:
                    pair = state['layer'], state['index']
                    if pair in targets[key] and speed(state, values, .125) != speed(state, values, 9):
                        legacy_failures.add((key, *pair))
assert len(legacy_failures) == expected_legacy_failures == 35
assert sum(key == '5266d735100376cc' for key, *_ in legacy_failures) == 5

# The present controllers don't reference the reserved slot, but future ones
# may. Cover both expression operands and TIME_STATE's direct variable index.
key = '5266d735100376cc'
synthetic = bytearray((ASSETS / (key + '.state_machine')).read_bytes())
parsed = Reader(synthetic).read(); last = parsed['names']['count'] - 1
state = next(s for s in parsed['states'] if (s['layer'], s['index']) not in targets[key] and s['words'])
S.pack_into('<I', synthetic, state['program']['data'], VARIABLE + last)
S.pack_into('<I', synthetic, state['start'] + 24, 3)
S.pack_into('<I', synthetic, state['end'] - 12, last)
_, variables, changes = transform(bytes(synthetic), targets[key])
assert sum(x.get('kind') == 'reserved_reference' for x in changes) >= 1
assert sum(x.get('kind') == 'reserved_time_state' for x in changes) >= 1
S.pack_into('<I', synthetic, parsed['names']['end'] - 4, 0xdeadbeef)
try:
    transform(bytes(synthetic), targets[key])
except AssertionError as error:
    assert 'Unknown reserved' in str(error)
else:
    raise AssertionError('Unknown resource layout was accepted')

# Run native Crusher attack timing with Havoc and red-stimm stat totals. The
# condition retimes its own animation/hits; native recovery limiting still runs.
import contextlib, io, runpy
with contextlib.redirect_stdout(io.StringIO()):
    env = runpy.run_path(str(PROJECT / 'tests/fixtures/frenzied_native_test_environment.py'))
L, native_source = env['L'], env['native']
timing = L.execute((PROJECT / 'src/HavocConditionPacks/diy/packages/starter-conditions-frenzied_assault/lua/timing.lua').read_text(encoding='utf-8'))
resource = L.execute((PROJECT / 'src/HavocConditionPacks/diy/packages/starter-conditions-frenzied_assault/lua/resources.lua').read_text(encoding='utf-8'))
assert timing['rate'] == 1.2
L.execute('''
modules['scripts/settings/damage/damage_profile_templates']=setmetatable({},{__index=function()return {}end})
modules['scripts/settings/fx/ground_impact_fx_templates']={}
modules['scripts/utilities/attack/hit_zone']={hit_zone_names=setmetatable({},{__index=function(_,k)return k end})}
modules['scripts/extension_systems/behavior/utility_considerations']={}
Managers.player={human_players=function()return {}end}
function crusher_case(data,event,speed)
 local u,b=unit();b.name='chaos_ogryn_executor'
 u.ext.buff_system.stat_buffs=function()return {melee_attack_speed=speed}end
 local pad={};local bb={perception={target_unit=target},behavior={},spawn={game_session=Managers.state.game_session,game_object_id=1}}
 local selected={};for k,v in pairs(data)do selected[k]=v end
 selected.attack_anim_events={event}
 BtMeleeAttackAction.enter(BtMeleeAttackAction,u,b,bb,pad,selected,10)
 return pad.attack_timing-10,pad.attack_duration-10
end
''')
actions = L.execute(native_source('scripts/settings/breed/breed_actions/chaos/chaos_ogryn_executor_actions.lua'))
native_cases = []
for kind, events in [('melee_attack', ['attack_03','attack_04','attack_05','attack_06']),
                     ('melee_attack_cleave', ['attack_01','attack_02','attack_07','attack_08'])]:
    raw = actions[kind]; prepared = timing.prepare(raw, resource['events'])
    for event in events:
        base_hit, base_end = L.globals().crusher_case(raw, event, 1)
        for label, data, multiplier, rate in [('native',raw,1,1), ('havoc5',raw,2,1),
                ('condition20',prepared,1,1.2), ('condition20_havoc5',prepared,2,1.2),
                ('condition20_havoc5_red',prepared,2.4,1.2)]:
            hit, end = L.globals().crusher_case(data, event, multiplier)
            assert math.isclose(hit, base_hit/rate, abs_tol=1e-9)
            assert math.isclose(end, max(base_end/rate/multiplier, hit+.2666666667), abs_tol=1e-8)
            native_cases.append(dict(event=event, scenario=label, hit=hit, end=end))

report = dict(patches=54, controller_copies=copies, controllers=len(shipped),
    melee_states=sum(map(len, targets.values())), speed_evaluations=checks,
    old_release_failures_detected=len(legacy_failures), fixed_failures=0,
    crusher_alternation=True, reserved_reference_remapping=True, native_crusher_timings=native_cases,
    limitation='Offline engine-table model and real binary resources; no live graphics-engine execution.')
(CHECKS / 'native-melee-resources.json').write_text(json.dumps(report, indent=2))
print('Native melee resources: 21 controllers / 262 states, 35 old faults reproduced, zero fixed faults: PASS')
