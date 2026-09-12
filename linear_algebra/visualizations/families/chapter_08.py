from __future__ import annotations
import json
import numpy as np
from ..compiler import CompileIssue, VisualCompileError
from linear_algebra.chapter_08_semantics import spec_for
from .quadratic import classify_quadratic
from .quadratic import QuadraticFamilyCompiler

TOL=1e-9
def _eq(a,b,name):
    if np.asarray(a).shape!=np.asarray(b).shape or not np.allclose(a,b,atol=TOL,rtol=0): raise ValueError(name+' disagrees with numerical evidence')

def compile_chapter_08(topic, semantics, context=None):
  try:
    spec=spec_for(topic); entities={e.role:e for e in semantics.entities}; vals={r:np.asarray(e.value,dtype=float) for r,e in entities.items()}
    if tuple(entities)!=spec.roles or len(entities)!=len(semantics.entities): raise ValueError('exact entity roles required')
    if semantics.scene_family!='quadratic_level_set' or semantics.scene_kind!='2d': raise ValueError('quadratic scene mismatch')
    for d in spec.entities:
      e=entities[d.role]
      if (e.id,e.kind,e.dimension,e.label)!=(f'entity.{topic}.{d.role}',d.kind,d.dimension,d.label): raise ValueError('entity descriptor mismatch')
    rels={d.name:r for d,r in zip(spec.relations,semantics.relations)}
    if tuple(r.id for r in semantics.relations)!=tuple(f'relation.{topic}.{d.name}' for d in spec.relations): raise ValueError('relation identities mismatch')
    for d in spec.relations:
      r=rels[d.name]
      if (r.kind,r.source_ref,r.target_ref,set(r.parameters))!=(d.kind,entities[d.source_role].id,entities[d.target_role].id,set(d.parameter_names)): raise ValueError('relation descriptor mismatch')
    if len(semantics.stages)!=len(spec.stages): raise ValueError('stage count mismatch')
    for s,d in zip(semantics.stages,spec.stages):
      if (s.id,s.title,s.caption,s.layout,tuple(s.input_entity_refs),tuple(s.output_entity_refs),tuple(s.relation_refs),tuple(s.expected_invariants))!=(d.name,d.title,spec.formula,d.layout,tuple(entities[x].id for x in d.input_roles),tuple(entities[x].id for x in d.output_roles),tuple(rels[x].id for x in d.relation_names),d.invariants): raise ValueError('stage descriptor mismatch')
    evidence={}
    for d in spec.entities:
      if vals[d.role].shape!=np.asarray(d.value).shape or not np.isfinite(vals[d.role]).all(): raise ValueError('nonfinite entity or shape')
    for relation in rels.values():
      for name,value in relation.parameters.items():
        if name in vals and name not in ('value','rank','classification','signature'): _eq(value,vals[name],'relation '+name)
    if topic=='ch08.principal-axis':
      a,q,d=vals['matrix'],vals['axes'],vals['standard']; _eq(q.T@q,np.eye(2),'orthogonal axes'); _eq(q.T@a@q,d,'principal diagonal')
      _eq(d,np.diag(np.diag(d)),'no cross term')
      _eq(rels['orthogonal_axes'].parameters['eigenvalues'],np.diag(d),'eigenvalues')
      _eq(a@q,q@d,'eigen axes'); _eq(vals['coordinates'],q.T@vals['point'],'rotated coordinates')
      _eq(rels['standard_form'].parameters['signature'],classify_quadratic(a).signature,'signature')
      _eq(vals['point']@a@vals['point'],vals['coordinates']@d@vals['coordinates'],'quadratic value')
      cross=float(abs(2*(q.T@a@q)[0,1])); endpoint=float(np.linalg.norm(q@vals['coordinates']-vals['point']))
      evidence.update(cross_term_after=cross,cross_term_after_rotation=cross,endpoint_error=endpoint,classification=classify_quadratic(a).classification)
    elif topic=='ch08.congruence-inertia':
      a,c,b=vals['matrix'],vals['substitution'],vals['congruent']; _eq(c.T@a@c,b,'congruence'); evidence['signature']=classify_quadratic(a).signature; evidence['rank']=int(np.linalg.matrix_rank(a))
      if abs(np.linalg.det(c))<TOL or np.allclose(c.T@c,np.eye(2)): raise ValueError('nonorthogonal invertible congruence required')
      _eq(classify_quadratic(b).signature,evidence['signature'],'inertia preservation')
      _eq(rels['congruence'].parameters['signature'],evidence['signature'],'declared inertia'); _eq(rels['congruence'].parameters['rank'],evidence['rank'],'rank')
      _eq(c@vals['coordinates'],vals['point'],'substitution'); _eq(rels['substitution'].parameters['value'],vals['point']@a@vals['point'],'value'); _eq(vals['point']@a@vals['point'],vals['coordinates']@b@vals['coordinates'],'congruent value')
    elif topic=='ch08.completing-square':
      a,c,d=vals['matrix'],vals['substitution'],vals['standard']; _eq(c.T@a@c,d,'complete square'); evidence['signature']=classify_quadratic(a).signature
      if abs(np.linalg.det(c))<TOL: raise ValueError('invertible substitution required')
      _eq(d,np.diag(np.diag(d)),'square form'); _eq(rels['complete_square'].parameters['square_weights'],np.diag(d),'square weights')
      _eq(c@vals['coordinates'],vals['point'],'substitution'); _eq(rels['substitution'].parameters['value'],vals['point']@a@vals['point'],'value'); _eq(vals['point']@a@vals['point'],vals['coordinates']@d@vals['coordinates'],'square value')
    elif topic=='ch08.quadratic.matrix-form':
      a=vals['matrix']; _eq(a,a.T,'symmetric'); p=vals['point']; _eq(a@p,vals['image'],'evaluation image'); _eq([float(p@a@p),0],vals['value'],'evaluation value'); evidence['classification']=classify_quadratic(a).classification
      _eq(vals['coefficients'],[a[0,0],2*a[0,1],a[1,1]],'cross coefficient')
      _eq(rels['evaluation'].parameters['value'],float(p@a@p),'relation value')
    elif topic=='ch08.quadratic.level-sets':
      a,b,q=vals['aligned'],vals['tilted'],vals['rotation']; _eq(a,np.diag(np.diag(a)),'aligned'); _eq(q.T@q,np.eye(2),'rotation'); _eq(b,q@a@q.T,'tilted ellipse'); evidence['signature']=classify_quadratic(b).signature
      params=rels['level_comparison'].parameters; _eq(params['eigenvalues'],classify_quadratic(a).eigenvalues,'level eigenvalues'); _eq(params['signature'],evidence['signature'],'level signature'); _eq(params['level'],1.,'unit level')
    else:
      evidence['classifications']={r:classify_quadratic(vals[r]).classification for r in ('positive','indefinite','semidefinite')}; evidence['signatures']={r:classify_quadratic(vals[r]).signature for r in ('positive','indefinite','semidefinite')}
      for name in evidence['classifications']:
        c=classify_quadratic(vals[name]); params=rels[name].parameters
        _eq(params['matrix'],vals[name],'state matrix'); _eq(params['eigenvalues'],c.eigenvalues,'state eigenvalues'); _eq(params['signature'],c.signature,'state signature')
        if c.classification!=('positive_definite' if name=='positive' else name): raise ValueError('classification state mismatch')
    evidence['invariants']={x:True for x in spec.invariants}; ops=[]; aliases={}
    def add(k,o): ops.append(o); aliases.setdefault(k,[]).append(o['alias'])
    def quadratic(key,matrix,alias):
      op=dict(QuadraticFamilyCompiler.compile({'matrix':np.asarray(matrix).tolist(),'bounds':[-3.,3.,-3.,3.],'sample_count':4096})['operations'][0])
      op.update(alias=alias,aliases=[alias,alias+'__principal',alias+'__standard']); add(key,op)
    def grid(key,matrix,alias): add(key,{'op':'geometry.transformed_grid','alias':alias,'matrix':np.asarray(matrix).tolist(),'bounds':[-3.,3.,-3.,3.],'step':1.})
    def transform(key,matrix,point,alias): add(key,{'op':'geometry.staged_transform','alias':alias,'matrices':[np.asarray(matrix).tolist()],'points':[np.asarray(point).tolist()],'aliases':[alias+'__point']})
    def vector(key,point,alias):
      ops.extend(({'op':'point.upsert','alias':alias+'__start','coordinates':[0.,0.]},{'op':'point.upsert','alias':alias+'__end','coordinates':np.asarray(point).tolist()}))
      add(key,{'op':'linear.upsert','alias':alias,'kind':'vector','start':alias+'__start','end':alias+'__end'})
    for d in spec.entities:
      key=entities[d.role].id; alias=f'{topic}__entity__{d.role}'
      if d.role in ('axes','rotation','substitution'): grid(key,vals[d.role],alias)
      elif d.kind=='matrix': quadratic(key,vals[d.role],alias)
      elif d.role=='coefficients':
        for i,value in enumerate(vals[d.role]): add(key,{'op':'point.upsert','alias':alias+f'__coefficient_{i}','coordinates':[float(i),float(value)],'name':('x²','xy','y²')[i]})
      elif d.kind=='point': add(key,{'op':'point.upsert','alias':alias,'coordinates':vals[d.role].tolist(),'name':d.role})
      else: vector(key,vals[d.role],alias)
    def relation(name,key,alias):
      if name=='coefficient_map': quadratic(key,vals['matrix'],alias)
      elif name=='evaluation': transform(key,vals['matrix'],vals['point'],alias)
      elif name=='level_comparison':
        quadratic(key,vals['aligned'],alias+'__aligned'); quadratic(key,vals['tilted'],alias+'__tilted')
      elif name=='orthogonal_axes':
        quadratic(key,vals['matrix'],alias+'__form')
        for i,column in enumerate(vals['axes'].T): vector(key,column,alias+f'__axis_{i}')
      elif name=='rotation': transform(key,vals['axes'].T,vals['point'],alias)
      elif name in ('standard_form','complete_square','congruence'):
        dest='congruent' if name=='congruence' else 'standard'
        quadratic(key,vals['matrix'],alias+'__original'); quadratic(key,vals[dest],alias+'__result')
      elif name=='substitution': transform(key,vals['substitution'],vals['coordinates'],alias)
      else: quadratic(key,vals[name],alias)
    for d in spec.relations: relation(d.name,rels[d.name].id,f'{topic}__relation__{d.name}')
    for d,stage in zip(spec.stages,semantics.stages):
      alias=f'{topic}__stage__{d.name}'
      if topic=='ch08.principal-axis':
        if d.name=='original': quadratic(stage.id,vals['matrix'],alias)
        elif d.name=='axes':
          grid(stage.id,vals['axes'],alias+'__axes'); transform(stage.id,vals['axes'].T,vals['point'],alias+'__rotation')
        else: quadratic(stage.id,vals['standard'],alias)
      elif topic=='ch08.quadratic.level-sets': quadratic(stage.id,vals[d.name],alias)
      else:
        for name in d.relation_names: relation(name,stage.id,alias+'__'+name)
    return json.loads(json.dumps({'operations':ops,'aliases':aliases,'evidence':evidence}))
  except (ValueError,TypeError,KeyError,np.linalg.LinAlgError) as error: raise VisualCompileError((CompileIssue('invalid_chapter_08_semantics','$.visual_semantics',str(error)),)) from error
