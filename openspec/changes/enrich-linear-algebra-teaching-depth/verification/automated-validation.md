# Automated Validation

Topic digests: 54

## python-validation
- command: `D:\anaconda3\python.exe -m linear_algebra.validation`
- exit code: 0
- output:
```text
54 topics validated
```

## python-tests
- command: `D:\anaconda3\python.exe -m pytest -q`
- exit code: 0
- output:
```text
........................................................................ [ 10%]
........................................................................ [ 21%]
........................................................................ [ 31%]
........................................................................ [ 42%]
........................................................................ [ 53%]
........................................................................ [ 63%]
........................................................................ [ 74%]
........................................................................ [ 85%]
........................................................................ [ 95%]
.............................                                            [100%]
============================== warnings summary ===============================
..\..\anaconda3\Lib\site-packages\paramiko\pkey.py:82
  D:\anaconda3\Lib\site-packages\paramiko\pkey.py:82: CryptographyDeprecationWarning: TripleDES has been moved to cryptography.hazmat.decrepit.ciphers.algorithms.TripleDES and will be removed from cryptography.hazmat.primitives.ciphers.algorithms in 48.0.0.
    "cipher": algorithms.TripleDES,

..\..\anaconda3\Lib\site-packages\paramiko\transport.py:243
  D:\anaconda3\Lib\site-packages\paramiko\transport.py:243: CryptographyDeprecationWarning: TripleDES has been moved to cryptography.hazmat.decrepit.ciphers.algorithms.TripleDES and will be removed from cryptography.hazmat.primitives.ciphers.algorithms in 48.0.0.
    "class": algorithms.TripleDES,

tests\test_ui_only.py:12
  D:\github\Math3DTeaching\tests\test_ui_only.py:12: PytestCollectionWarning: cannot collect test class 'TestWindow' because it has a __init__ constructor (from: tests/test_ui_only.py)
    class TestWindow(QMainWindow):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
677 passed, 3 warnings in 28.03s
```

## web-tests
- command: `C:\Program Files\nodejs\pnpm.CMD --dir ui/agent_web test -- --run`
- exit code: 0
- output:
```text

 RUN  v2.1.9 D:/github/Math3DTeaching/ui/agent_web

 ✓ src/styles/layout.test.ts (3 tests) 10ms
 ✓ src/styles/theme.test.ts (3 tests) 5ms
 ✓ src/components/SessionTabs.test.tsx (3 tests) 151ms
 ✓ src/state/reducer.test.ts (14 tests) 11ms
 ✓ src/components/ModelSelector.test.tsx (4 tests) 184ms
 ✓ src/bridge/qtBridge.test.ts (3 tests) 8ms
 ✓ src/components/Timeline.test.tsx (3 tests) 209ms
 ✓ src/components/HistoryView.test.tsx (4 tests) 223ms
 ✓ src/components/Composer.test.tsx (3 tests) 169ms
 ✓ src/components/MathCaseView.structured.test.tsx (1 test) 168ms
 ✓ src/App.test.tsx (4 tests) 333ms
 ✓ src/state/theme.test.ts (2 tests) 4ms
 ✓ src/components/EventCard.test.tsx (2 tests) 47ms
 ✓ src/components/PlanCard.test.tsx (1 test) 37ms
 ✓ src/components/MarkdownContent.test.tsx (1 test) 58ms
 ✓ src/components/SessionTabs.case.test.tsx (1 test) 69ms
 ✓ src/components/MathCaseView.test.tsx (1 test) 89ms

 Test Files  17 passed (17)
      Tests  53 passed (53)
   Start at  02:29:31
   Duration  7.22s (transform 891ms, setup 10.66s, collect 4.00s, tests 1.78s, environment 36.59s, prepare 7.29s)

$ vitest run "--" "--run"
```

## web-build
- command: `C:\Program Files\nodejs\pnpm.CMD --dir ui/agent_web build`
- exit code: 0
- output:
```text
vite v6.4.3 building for production...
transforming...
✓ 1673 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                         0.71 kB │ gzip:   0.40 kB
dist/assets/KaTeX_Size3-Regular-CTq5MqoE.woff           4.42 kB
dist/assets/KaTeX_Size4-Regular-Dl5lxZxV.woff2          4.93 kB
dist/assets/KaTeX_Size2-Regular-Dy4dx90m.woff2          5.21 kB
dist/assets/KaTeX_Size1-Regular-mCD8mA8B.woff2          5.47 kB
dist/assets/KaTeX_Size4-Regular-BF-4gkZK.woff           5.98 kB
dist/assets/KaTeX_Size2-Regular-oD1tc_U0.woff           6.19 kB
dist/assets/KaTeX_Size1-Regular-C195tn64.woff           6.50 kB
dist/assets/KaTeX_Caligraphic-Regular-Di6jR-x-.woff2    6.91 kB
dist/assets/KaTeX_Caligraphic-Bold-Dq_IR9rO.woff2       6.91 kB
dist/assets/KaTeX_Size3-Regular-DgpXs0kz.ttf            7.59 kB
dist/assets/KaTeX_Caligraphic-Regular-CTRA-rTL.woff     7.66 kB
dist/assets/KaTeX_Caligraphic-Bold-BEiXGLvX.woff        7.72 kB
dist/assets/KaTeX_Script-Regular-D3wIWfF6.woff2         9.64 kB
dist/assets/KaTeX_SansSerif-Regular-DDBCnlJ7.woff2     10.34 kB
dist/assets/KaTeX_Size4-Regular-DWFBv043.ttf           10.36 kB
dist/assets/KaTeX_Script-Regular-D5yQViql.woff         10.59 kB
dist/assets/KaTeX_Fraktur-Regular-CTYiF6lA.woff2       11.32 kB
dist/assets/KaTeX_Fraktur-Bold-CL6g_b3V.woff2          11.35 kB
dist/assets/KaTeX_Size2-Regular-B7gKUWhC.ttf           11.51 kB
dist/assets/KaTeX_SansSerif-Italic-C3H0VqGB.woff2      12.03 kB
dist/assets/KaTeX_SansSerif-Bold-D1sUS0GD.woff2        12.22 kB
dist/assets/KaTeX_Size1-Regular-Dbsnue_I.ttf           12.23 kB
dist/assets/KaTeX_SansSerif-Regular-CS6fqUqJ.woff      12.32 kB
dist/assets/KaTeX_Caligraphic-Regular-wX97UBjC.ttf     12.34 kB
dist/assets/KaTeX_Caligraphic-Bold-ATXxdsX0.ttf        12.37 kB
dist/assets/KaTeX_Fraktur-Regular-Dxdc4cR9.woff        13.21 kB
dist/assets/KaTeX_Fraktur-Bold-BsDP51OF.woff           13.30 kB
dist/assets/KaTeX_Typewriter-Regular-CO6r4hn1.woff2    13.57 kB
dist/assets/KaTeX_SansSerif-Italic-DN2j7dab.woff       14.11 kB
dist/assets/KaTeX_SansSerif-Bold-DbIhKOiC.woff         14.41 kB
dist/assets/KaTeX_Typewriter-Regular-C0xS9mPB.woff     16.03 kB
dist/assets/KaTeX_Math-BoldItalic-CZnvNsCZ.woff2       16.40 kB
dist/assets/KaTeX_Math-Italic-t53AETM-.woff2           16.44 kB
dist/assets/KaTeX_Script-Regular-C5JkGWo-.ttf          16.65 kB
dist/assets/KaTeX_Main-BoldItalic-DxDJ3AOS.woff2       16.78 kB
dist/assets/KaTeX_Main-Italic-NWA7e6Wa.woff2           16.99 kB
dist/manifest.json                                     18.52 kB │ gzip:   1.62 kB
dist/assets/KaTeX_Math-BoldItalic-iY-2wyZ7.woff        18.67 kB
dist/assets/KaTeX_Math-Italic-DA0__PXp.woff            18.75 kB
dist/assets/KaTeX_Main-BoldItalic-SpSLRI95.woff        19.41 kB
dist/assets/KaTeX_SansSerif-Regular-BNo7hRIc.ttf       19.44 kB
dist/assets/KaTeX_Fraktur-Regular-CB_wures.ttf         19.57 kB
dist/assets/KaTeX_Fraktur-Bold-BdnERNNW.ttf            19.58 kB
dist/assets/KaTeX_Main-Italic-BMLOBm91.woff            19.68 kB
dist/assets/KaTeX_SansSerif-Italic-YYjJ1zSn.ttf        22.36 kB
dist/assets/KaTeX_SansSerif-Bold-CFMepnvq.ttf          24.50 kB
dist/assets/KaTeX_Main-Bold-Cx986IdX.woff2             25.32 kB
dist/assets/KaTeX_Main-Regular-B22Nviop.woff2          26.27 kB
dist/assets/KaTeX_Typewriter-Regular-D3Ib7_Hf.ttf      27.56 kB
dist/assets/KaTeX_AMS-Regular-BQhdFMY1.woff2           28.08 kB
dist/assets/KaTeX_Main-Bold-Jm3AIy58.woff              29.91 kB
dist/assets/KaTeX_Main-Regular-Dr94JaBh.woff           30.77 kB
dist/assets/KaTeX_Math-BoldItalic-B3XSjfu4.ttf         31.20 kB
dist/assets/KaTeX_Math-Italic-flOr_0UB.ttf             31.31 kB
dist/assets/KaTeX_Main-BoldItalic-DzxPMmG6.ttf         32.97 kB
dist/assets/KaTeX_AMS-Regular-DMm9YOAa.woff            33.52 kB
dist/assets/KaTeX_Main-Italic-3WenGoN9.ttf             33.58 kB
dist/assets/KaTeX_Main-Bold-waoOVXN0.ttf               51.34 kB
dist/assets/KaTeX_Main-Regular-ypZvNtVU.ttf            53.58 kB
dist/assets/KaTeX_AMS-Regular-DRggAlZN.ttf             63.63 kB
dist/assets/index-D4YoIuUf.css                         50.34 kB │ gzip:  12.56 kB
dist/assets/index-BKlbGOaE.js                         598.48 kB │ gzip: 197.29 kB
✓ built in 2.74s
$ pnpm theme:generate
$ node scripts/gen-theme.mjs
$ vite build

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking: https://rollupjs.org/configuration-options/#output-manualchunks
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```
