# AI 学习上手包（第 1-3 周可运行代码）

配套文件：`AI学习路线_16周计划表.xlsx`（总路线）+ `AI学习_上手手册.md`（逐小时步骤）

你的机器已确认有：Windows 11、系统 Python 3.11.9、Git 2.56、VS Code、Anaconda（base 环境包很全）。
**`.venv` 虚拟环境骨架已经帮你建好了**（位置 `ai-starter\.venv`，Python 3.11.9），
你只差一条装包命令就能开始（见下面第 3 步）。

---

## 3 分钟跑起来（PowerShell 照抄）

先按 `Win`，输入 `powershell`，回车打开。然后**逐条**复制下面的命令，每条按一次回车：

```powershell
cd "$env:USERPROFILE\OneDrive\Desktop\ai-starter"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
python week01\01_check_env.py
```

第 3 步约 2-5 分钟（下载 40MB 左右）。第 4 步看到 `虚拟环境: ✅ 已激活`、五个包全 ✅ 就成功了。

> 注意你的桌面在 **OneDrive** 下（`C:\Users\yan\OneDrive\Desktop`），不是 `C:\Users\yan\Desktop`。
> 上面第一条命令已经处理好了，直接复制即可。

### 如果 Activate.ps1 报"禁止运行脚本"

PowerShell 默认不让运行脚本文件。执行一次下面这条（只影响你自己的账户，安全）：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

然后**关掉这个窗口重开一个**，再从第 2 步继续。

### 每次都要记住的一件事

激活环境**不会永久生效**——每开一个新的 PowerShell 窗口都要重新
`.\.venv\Scripts\Activate.ps1`。命令行前面出现 `(.venv)` 才表示生效了。
**"忘了激活环境"是新手第一大坑。**

### 为什么不用 conda 新建环境（2026-10-22 实测记录）

我们实际试过 conda 路线，在你机器上连撞三堵墙：
1. 往 `D:\Anaconda3\envs` 写不进去（`NoWritableEnvsDirError`）；
2. 走中科大镜像时 TLS 被掐（`CondaSSLError`，镜像限流，网络本身没问题）；
3. 换清华源后又撞上 anaconda 官方频道要求登录（403）。

`.venv` 建在你自己的桌面目录里，零权限问题，效果与 conda 环境完全一样。

> 以后想用 conda 建环境，先跑一次
> `conda config --add envs_dirs C:\Users\yan\.conda\envs`
> 把环境目录指到你完全可写的位置即可。现在不用管。

---

## 文件清单

| 路径 | 是什么 | 对应周 |
|---|---|---|
| `week01\01_check_env.py` | 环境体检：解释器位置、包版本、虚拟环境是否激活 | W1 |
| `week01\02_merge_csv.py` | 本周交付物：合并目录下所有 CSV → 导出 Excel | W1 |
| `week01\03_organize.py` | 批量整理文件夹小工具（默认只预览，不动文件） | W1 |
| `week01\data\` | 3 份故意留了脏数据的示例 CSV，可直接跑 | W1 |
| `week02\01_api_fetch.py` | 调公开 API：超时 + 重试 + 多端点回退 | W2 |
| `week02\02_analyze_chart.py` | pandas 清洗聚合 → 导出带图表的 Excel | W2 |
| `week02\data\rates_sample.json` | 断网时的兜底样本数据 | W2 |
| `week03\01_preflight.py` | 仓库合规自查：git、README、.gitignore、密钥泄露 | W3 |
| `week03\02_key_test.py` | 最小密钥读取示范（含脱敏打印写法） | W3 |
| `week07\01_chat_cli.py` | 第 7 周的命令行对话程序（配好 key 就能跑） | W7 |
| `.env.example` | 密钥模板。**复制成 `.env` 用，不要改这个文件** | W3+ |
| `.gitignore` | 已配好，屏蔽 `.env`、`.venv`、缓存 | W3 |
| `requirements.txt` | 第 1-3 周所需依赖清单 | W1 |

---

## 每个脚本怎么自己试

> 下面假设你已经激活了 `.venv`（命令行前有 `(.venv)`）。
> 没激活的话，把 `python` 换成 `D:\Anaconda3\python.exe` 也能跑（Anaconda base 里包是全的）。

```powershell
python week01\02_merge_csv.py                       # 用默认的 week01\data
python week01\02_merge_csv.py D:\我的报表文件夹      # 换成你自己的目录
python week01\02_merge_csv.py --out 汇总.xlsx        # 指定输出文件名
python week01\03_organize.py "$env:USERPROFILE\Downloads"          # 先看预览，什么都不改
python week01\03_organize.py "$env:USERPROFILE\Downloads" --apply  # 确认预览没问题再真做
python week02\01_api_fetch.py --base EUR --targets CNY JPY --days 180
python week02\02_analyze_chart.py                   # 出 Excel + 趋势图
python week03\01_preflight.py                       # push 前必跑
```

第 3 个脚本**默认是预览模式**，必须显式加 `--apply` 才会移动文件。这是你以后写任何"会改数据的脚本"都要养成的习惯。

---

## 报错了怎么办

1. 复制**完整的红字**，不要只截最后一行。
2. 先看 `AI学习_上手手册.md` 第 6 节的「新手报错对照表」，15 个最常见错误都在里面（含 PowerShell 编码、GBK、pip 卡住、GitHub token 等）。
3. 找不到就把完整报错 + 最小复现代码拿去问 AI。**「能构造最小复现」是从新手到工程师的分水岭。**
