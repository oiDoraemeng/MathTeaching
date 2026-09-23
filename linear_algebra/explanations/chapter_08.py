from .model import ExplanationContent


_IDS = ("quadratic.matrix-form", "quadratic.level-sets", "principal-axis", "definiteness")


def _content(topic: str) -> ExplanationContent:
    from linear_algebra.chapter_08_semantics import spec_for

    spec = spec_for(topic)
    subject = {
        "quadratic.matrix-form": "二次型",
        "quadratic.level-sets": "二次型的几何意义",
        "principal-axis": "主轴定理",
        "definiteness": "定性：正定、负定、不定",
    }[topic]
    return ExplanationContent(
        id=f"explain.ch08.{topic}",
        title=subject,
        summary=subject,
        formula=spec.formula,
        steps=tuple(stage.title for stage in spec.stages),
        geometric_meaning="",
        conclusion="",
        searchable_text=(subject, spec.formula),
        numeric_example=spec.formula,
        pitfalls=(),
        read_guide=(),
        analogy_boundary="",
    )


EXPLANATIONS = {f"ch08.{topic}": _content(topic) for topic in _IDS}
CONTENT = EXPLANATIONS
