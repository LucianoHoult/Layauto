import sys,json,copy
from dataclasses import replace
from fractions import Fraction
sys.path.insert(0,'/workspace/work/w011-review-boundary-final')
from layauto_v2.domain.channel_identity import ChannelRef,FinEvaluation,ChannelMeasurement
from layauto_v2.domain.geometry import GeometryRecordId,Rect
from layauto_v2.domain.regions import RegionRef
from layauto_v2.domain.evidence import SourceRef
from layauto_v2.normalization.channel_identity_codec import encode_record,decode_record
channel=RegionRef('region','a'*64); binding=ChannelRef('binding','b'*64)
base=FinEvaluation(GeometryRecordId('c'*64),channel,'qualified',Rect(0,0,1,2),Fraction(2),SourceRef('review.gds','d'*64),binding)
rows=[]
try:replace(base,width_nm=2)
except ValueError as exc:rows.append({'case':'direct_invalid_leaf_constructor','rejected':True,'exception':type(exc).__name__,'message':str(exc)})
for scalar in (2,):
    forged=copy.deepcopy(base);object.__setattr__(forged,'width_nm',scalar)
    row={'case':'forged_nested_leaf_public_measurement','forged_width_type':type(scalar).__name__,'equal_to_original':forged==base,'uses_object_setattr_bypass':True}
    try:
        result=ChannelMeasurement(channel,GeometryRecordId('e'*64),Fraction(1),(forged,),1,(),binding)
        row.update(public_constructor_accepted=True,retained_width_type=type(result.evaluations[0].width_nm).__name__)
        try:decode_record(encode_record(result))
        except BaseException as exc:row.update(codec_rejected=True,exception=type(exc).__name__,message=str(exc))
        else:row['codec_rejected']=False
    except BaseException as exc:row.update(public_constructor_accepted=False,exception=type(exc).__name__,message=str(exc))
    rows.append(row)
print(json.dumps({'review_head':'8917d38d916c914bfa785cb116982f3f299b38de','results':rows},indent=2))
