from linear_algebra.catalog.chapter_08 import TOPICS
from linear_algebra.teaching.chapter_artifacts import artifact_payload_for
from linear_algebra.teaching.compile_resources import compile_chapter_08
def main():
    payloads={t.id:artifact_payload_for(t.id) for t in TOPICS}; resources=compile_chapter_08(reviewed_payloads=payloads); print(f'released {len(resources)} Chapter 8 reviewed and compiled resources'); return 0
if __name__=='__main__': raise SystemExit(main())
