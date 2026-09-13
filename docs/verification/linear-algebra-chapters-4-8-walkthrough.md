# 第 4–8 章逐章走查记录

以下记录来自同一 registry/compiled resource 读取路径，作为人工走查前的可重复预检。每个代表主题均有 revision、source hash、compiler version、plan digest 和阶段列表。

| 章节 | 代表主题 | revision | source hash | compiler | plan digest | 阶段 |
| --- | --- | ---: | --- | --- | --- | --- |
| 4 | `ch04.subspace.col-null` | 1 | `sha256:6d9a29e55f9a21b1846003bb5658be910fcd5cc07e231cbf3b4eec2335bb13d0` | `visual-compiler-v1` | `sha256:e70e289689a9b9cf640741e6517e88a621792a711d1e7fd99652e2c79d01e456` | domain, codomain |
| 5 | `ch05.consistency.geometry` | 1 | `sha256:1614e33fb06841af899d9a1dcb9db46a85a5e6cb14d681568ec2ba77c06c800e` | `visual-compiler-v1` | `sha256:0b656c3e141583a4b1acbc9f3a4c3adc45ca27db814169a0ad3a4c1fdd88a778` | unique, none, infinite |
| 6 | `ch06.similarity-transform` | 1 | `sha256:c700a7e3f54691290562a7c582245d08d693033604df782a6dbc475be605d7a7` | `visual-compiler-v1` | `sha256:8afb471a7eca866e08ffdc783e60641ee2fcef3c61854249c4f3cd11d0be613c` | change_basis, apply_operator, change_basis_back |
| 7 | `ch07.diagonalization` | 1 | `sha256:c370dc89d6decc1af953b64023d41ad23f8858ec9f3cdcac971a15bc36e8ff5a` | `visual-compiler-v1` | `sha256:94da29aea5ddff7f426686dee8e8f989e31c8bbb32fc6c7dc8b6d45be87c77b2` | change_basis, diagonal_scale, change_basis_back |
| 8 | `ch08.principal-axis` | 1 | `sha256:6070ef97f7c347269da95f348d213d97363fcd712afd7bcb3bc536bfbf4ed435` | `visual-compiler-v1` | `sha256:1c7f84ab180d0af124f128ca81f876183b06b9226cc259e869a06f01f96ceeb0` | original, axes, standard |

自动化预检确认：章节树、主题资源、阶段选择和失败回退测试均通过；未知阶段不会改变当前可见性。当前运行环境为无头 Qt，未生成真实桌面截图，也未将截图缺席误记为人工验收通过。
