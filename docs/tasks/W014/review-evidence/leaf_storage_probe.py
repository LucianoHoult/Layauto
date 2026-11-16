"""Independent tiny W014 retained-storage probe; no capture/local reconstruction."""
from __future__ import annotations

from dataclasses import replace
import json

from layauto_v2.domain.circuit import Terminal
from layauto_v2.domain.codec import canonical_bytes
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.domain.identifiers import CellId, DeviceId, NetId
from layauto_v2.domain.local_connectivity import LocalRef
from layauto_v2.domain.regions import RegionRef
from layauto_v2.domain.terminal_relations import TerminalRef, TerminalRelation, TerminalTarget


def make():
    cell=CellId('LEAF')
    net=NetId(cell,'Y')
    return TerminalRelation(TerminalTarget(TerminalRef('binding','a'*64), DeviceId(cell,'MN0'),'D'),
        Terminal('D',net,SourceRef('source.cdl','b'*64,line=3)),RegionRef('region','c'*64),
        (LocalRef('node','d'*64),),(LocalRef('component','e'*64),),(),(net,),(),None,(net,),'established')


def main():
    results=[]
    for name, select in (
        ('source_ref',lambda r:r.expected.source),
        ('terminal',lambda r:r.expected),
        ('device_id',lambda r:r.target.device_id),
        ('cell_id',lambda r:r.target.device_id.cell),
        ('net_id',lambda r:r.expected.net_id),
        ('node_ref',lambda r:r.node_refs[0]),
    ):
        row=make()
        leaf=select(row)
        alias=[]
        object.__setattr__(leaf,'undeclared_extra',alias)
        try:
            cloned=replace(row)
            before=canonical_bytes(cloned.to_value())
            alias.append('changed')
            after=canonical_bytes(cloned.to_value())
        except ValueError as exc:
            results.append({'leaf':name,'rejected':True,'error':str(exc)})
        else:
            results.append({'leaf':name,'rejected':False,'retains_alias':select(cloned).undeclared_extra is alias,
                'wire_ignores_alias_mutation':before==after})
    print(json.dumps({'probe':'W014 retained nested leaf storage','results':results},indent=2))


if __name__=='__main__':main()
