"""Bounded read of extracted Darktide state-machine serialization (not live memory).
Format cross-checked against Bitsquid Blender Tools, commit d8061ad4, GPL-3.0
reference files retained in vendor/. No changes to game resources.
"""
from pathlib import Path
import struct as S,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]/'build'
sys.path.insert(0,str(ROOT))
from audit_enemy_assets import h
ASSETS=ROOT/'enemy-animation-assets'
class Reader:
    def __init__(self,data):self.data=data;self.pos=0;self.arrays=[]
    def take(self,n):
        assert 0<=n<=len(self.data)-self.pos,(self.pos,n,len(self.data))
        p=self.pos;self.pos+=n;return p
    def u(self):return S.unpack_from('<I',self.data,self.take(4))[0]
    def q(self):return S.unpack_from('<Q',self.data,self.take(8))[0]
    def count(self,limit=20000):
        n=self.u();assert n<=limit,(self.pos,n);return n
    def array(self,width):
        start=self.pos;n=self.count();pos=self.take(n*width)
        result={'start':start,'data':pos,'count':n,'width':width,'end':self.pos}
        self.arrays.append(result);return result
    def words(self,a):return list(S.unpack_from('<'+'I'*a['count'],self.data,a['data']))
    def state(self,layer,index):
        start=self.pos
        ids=[self.q(),self.q(),self.q()];kind=self.u()
        assert kind<=5,(start,kind)
        animations=self.array(8);probabilities=self.array(4)
        self.take(9)
        transitions=self.array(9);blend=self.array(28)
        switches=[]
        for _ in range(self.count()):
            switches.append({'bytecode':self.u(),'exits':self.array(14)})
        self.take(8);timeline=self.array(12);self.take(8)
        program=self.array(4);weights=self.array(4)
        fields_start=self.pos;fields=[self.u() for _ in range(4)]
        constraints=self.array(4);tail=[self.u() for _ in range(3)]
        return {'layer':layer,'index':index,'start':start,'end':self.pos,'ids':ids,'kind':kind,
        'program':program,'words':self.words(program),'weights':self.words(weights),
        'fields':fields,'tail':tail,'transitions':transitions,'blend':blend,
        'animations':animations,'probabilities':probabilities,'switches':switches,
        'weights_array':weights,'fields_start':fields_start}
    def read(self):
        states=[];layer_counts=[]
        for layer in range(self.count(32)):
            count=self.count(1000);layer_counts.append(count)
            states.extend(self.state(layer,i) for i in range(count));self.take(4)
        events=self.array(4);names=self.array(4);defaults=self.array(4);bounds=self.array(8)
        assert names['count']==defaults['count']==bounds['count']
        for _ in range(self.count(1000)):
            self.array(4);self.array(4);self.take(1)
        self.array(4);self.array(12);self.array(1)
        for _ in range(self.count(1000)):self.array(4);self.array(4)
        self.array(28);self.take(4)
        assert self.pos==len(self.data),(self.pos,len(self.data))
        return {'layers':layer_counts,'states':states,'events':events,'names':names,
        'defaults':defaults,'bounds':bounds,'parsed_bytes':self.pos}
if __name__=='__main__':
    coverage=json.loads((ASSETS/'movement-coverage.json').read_text())
    resources={a['hash'] for row in coverage for a in row['assets']}
    names={h(s):s for s in json.loads((ASSETS/'native_tokens.json').read_text())}
    report=[]
    for key in sorted(resources):
        data=(ASSETS/(key+'.state_machine')).read_bytes()
        try:
            r=Reader(data).read()
            for state in r['states']:
                state['name']=names.get(state['ids'][1],f"{state['ids'][1]:016x}")
            out=Path(__file__).parent/(key+'.json')
            out.write_text(json.dumps(r,indent=2),encoding='utf-8')
            row={'resource':key,'bytes':len(data),'states':len(r['states']),
            'layers':r['layers'],'variables':r['names']['count'],'full_parse':True}
        except Exception as e:row={'resource':key,'full_parse':False,'error':str(e)[:180]}
        report.append(row)
    (Path(__file__).parent/'parse-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
