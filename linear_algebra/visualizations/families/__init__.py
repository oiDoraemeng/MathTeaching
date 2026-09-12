"""Explicit semantic scene-family dispatch registry."""
from dataclasses import dataclass
from ..compiler import VisualCompileError, CompileIssue
from .subspace import SubspaceFamilyCompiler, SubspaceCompileResult
from .tableau import MatrixTableauCompiler, TableauCompileResult, TableauStage, Swap, Scale, Eliminate, apply_row_operation
from .coordinates import CoordinateFamilyCompiler, CoordinateEvidence, coordinate_evidence
from .least_squares import LeastSquaresFamilyCompiler, LeastSquaresEvidence, least_squares_fit
from .spectral import SpectralFamilyCompiler, SpectralEvidence, SpectralRoot, spectral_evidence
from .orthogonalization import OrthogonalizationFamilyCompiler, OrthogonalizationEvidence, gram_schmidt
from .quadratic import QuadraticFamilyCompiler, QuadraticEvidence, classify_quadratic
from .chapter_04 import Chapter4FamilyCompiler, Chapter4CompileResult, compile_chapter_04
from .chapter_05 import compile_chapter_05
from .chapter_06 import compile_chapter_06
from .chapter_07 import compile_chapter_07
from .constraints import ConstraintFamilyCompiler


@dataclass(frozen=True)
class SceneFamilyCompiler:
    primitive: str

    def compile(self, *args, **kwargs):
        semantics = kwargs.get('semantics')
        topic = kwargs.get('topic_id')
        if isinstance(topic, str) and semantics is not None:
            if topic.startswith('ch04.'):
                return compile_chapter_04(topic, semantics, kwargs.get('context'))
            if topic.startswith('ch05.'):
                return compile_chapter_05(topic, semantics)
            if topic.startswith('ch06.'):
                return compile_chapter_06(topic, semantics, kwargs.get('context'))
            if topic.startswith('ch07.'):
                return compile_chapter_07(topic, semantics, kwargs.get('context'))
        return {'family': self.primitive, 'validated': True}


_REGISTERED = {name: SceneFamilyCompiler(name) for name in (
    'subspace_region', 'affine_solution', 'basis_change', 'spectral_orthogonal', 'quadratic_level_set')}


def family_compiler_for(primitive):
    try:
        return _REGISTERED[primitive]
    except KeyError as error:
        raise VisualCompileError((CompileIssue('unsupported_scene_family', '$.visual_semantics.scene_family', f'unsupported_scene_family: {primitive}'),)) from error


def registered_families():
    return tuple(sorted(_REGISTERED))
