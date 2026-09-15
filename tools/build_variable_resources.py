"""Build an OFFLINE experiment; never modify an installed game resource.

Keep bytecode length and ordinary original variable indices unchanged. Replace only
the constant operand of confirmed melee playback expressions with a variable
whose default is that exact constant. Format references live beside the parser.
"""
from pathlib import Path
import argparse, collections, hashlib, json, math, struct as S
from inspect_controllers import Reader, ASSETS, h

HERE = Path(__file__).parent
OUT = HERE.parent / 'build/variable-resources-v2'
RATE = 1.2
STOP, VARIABLE = 0x7fa00000, 0x7f900000
RESERVED_DURATION_HASH = 0x4781ca70


def transform(data, selected):
    before = Reader(data).read()
    states = {(s['layer'], s['index']): s for s in before['states']}
    constants = sorted({states[k]['words'][states[k]['fields'][0]] for k in selected})
    count = before['names']['count']
    original_order = S.unpack_from('<' + 'I' * count, data, before['names']['data'])
    # The engine overwrites the final entry in a temporary copy with the
    # current clip duration before evaluating playback speed. Keep that
    # reserved entry last; appending after it makes an ordinary speed variable
    # read the clip duration instead of the value written through Unit.
    assert count and original_order[-1] == RESERVED_DURATION_HASH, 'Unknown reserved animation variable layout'
    first = count - 1
    original_names = set(original_order)
    variables = []
    for i, bits in enumerate(constants):
        default = S.unpack('<f', S.pack('<I', bits))[0]
        assert math.isfinite(default) and default > 0
        name = f'hcm_melee_{bits:08x}'
        name_hash = h(name) >> 32
        assert name_hash not in original_names
        original_names.add(name_hash)
        variables.append(dict(name=name, hash=name_hash, index=first+i,
                              default=default, value=default*RATE, bits=bits))
    by_bits = {v['bits']: v for v in variables}
    changed = bytearray(data)
    operands = []
    moved_reserved = first + len(variables)
    for key, state in states.items():
        for offset, bits in enumerate(state['words']):
            if bits == VARIABLE + first:
                pos = state['program']['data'] + offset*4
                S.pack_into('<I', changed, pos, VARIABLE + moved_reserved)
                operands.append(dict(layer=key[0], state=key[1], offset=pos, bits=bits, kind='reserved_reference'))
        # TIME_STATE stores a direct variable index in its first tail field.
        if state['kind'] == 3 and state['tail'][0] == first:
            pos = state['end'] - 12
            S.pack_into('<I', changed, pos, moved_reserved)
            operands.append(dict(layer=key[0], state=key[1], offset=pos, bits=first, kind='reserved_time_state'))
    for key in sorted(selected):
        state = states[key]
        offset = state['fields'][0]
        bits = state['words'][offset]
        assert state['words'][offset+1] == STOP
        assert bits in by_bits
        pos = state['program']['data'] + offset*4
        S.pack_into('<I', changed, pos, VARIABLE + by_bits[bits]['index'])
        operands.append(dict(layer=key[0], state=key[1], offset=pos, bits=bits))
    arrays = (
        ('names', b''.join(S.pack('<I', v['hash']) for v in variables)),
        ('defaults', b''.join(S.pack('<I', v['bits']) for v in variables)),
        ('bounds', b''.join(S.pack('<ff', 0, 16) for v in variables)),
    )
    for key, extra in reversed(arrays):
        a = before[key]
        insert = a['end'] - a['width']
        changed[insert:insert] = extra
        S.pack_into('<I', changed, a['start'], a['count'] + len(variables))
    changed = bytes(changed)
    after = Reader(changed).read()
    assert after['layers'] == before['layers']
    assert len(after['states']) == len(before['states'])
    for key, _ in arrays:
        a, b = before[key], after[key]
        assert data[a['data']:a['end']-a['width']] == changed[b['data']:b['data']+first*b['width']]
        assert data[a['end']-a['width']:a['end']] == changed[b['end']-b['width']:b['end']]
    assert all(v['index'] < after['names']['count']-1 for v in variables)
    for a, b in zip(before['states'], after['states']):
        assert a['start'] == b['start'] and a['end'] == b['end']
        assert a['fields'] == b['fields'] and a['weights'] == b['weights']
        key = a['layer'], a['index']
        expected = [VARIABLE + moved_reserved if w == VARIABLE + first else w for w in a['words']]
        expected_tail = list(a['tail'])
        if a['kind'] == 3 and expected_tail[0] == first: expected_tail[0] = moved_reserved
        assert b['tail'] == expected_tail
        if key in selected:
            offset = a['fields'][0]
            v = by_bits[expected[offset]]
            expected[offset] = VARIABLE + v['index']
            assert abs((v['value'] / v['default']) - RATE) < 1e-12
        assert b['words'] == expected
    # Undo every authorized edit and require a byte-identical round trip.
    restored = bytearray(changed)
    for key, _ in reversed(arrays):
        a = after[key]
        old_count = before[key]['count']
        del restored[a['data'] + first*a['width']:a['end']-a['width']]
        S.pack_into('<I', restored, a['start'], old_count)
    for p in operands:
        S.pack_into('<I', restored, p['offset'], p['bits'])
    assert bytes(restored) == data
    return changed, variables, operands


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=OUT)
    output = parser.parse_args().output
    mapping = json.loads((HERE/'melee-state-map.json').read_text())
    targets = collections.defaultdict(set)
    for row in mapping['targets']:
        targets[row['asset']].add((row['layer'], row['index']))
    output.mkdir(exist_ok=True)
    resources = {}
    for key, selected in sorted(targets.items()):
        data = (ASSETS/(key+'.state_machine')).read_bytes()
        patched, variables, operands = transform(data, selected)
        (output/(key+'.state_machine')).write_bytes(patched)
        resources[key] = dict(source_sha256=hashlib.sha256(data).hexdigest(),
            output_sha256=hashlib.sha256(patched).hexdigest(), variables=variables,
            changes=operands, bytes=len(patched), byte_exact_undo=True, reserved_duration_slot_last=True)
    report = dict(status='offline resource experiment; engine loading unverified',
        rate=RATE, resources=resources, unresolved=mapping['missing'],
        total_states=sum(len(v['changes']) for v in resources.values()))
    (output/'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(rate=RATE, resources=len(resources), states=report['total_states'],
        variable_count=sum(len(v['variables']) for v in resources.values()),
        undo='byte exact for every resource', unresolved=report['unresolved']), indent=2))


if __name__ == '__main__':
    main()
