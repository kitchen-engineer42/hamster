# Hamster

> English: [`README.md`](README.md)

Hamster 产出一个**带版本、经过验证的 John 模板**：一个可移植的 diff，用来教 John 如何构建某一类知识密集型应用。你提供干净的 John checkout、原始领域输入、模板名和目标应用体验。Hamster 创建可写 fork，只打包受支持的变更，精确固定 John 版本，并在发布前真实应用产物。

Hamster 同等支持 **Claude Code、Codex 或两者同时使用**。共享 skills 和方法论字节一致；只有 provider 执行指导不同。

## 安装与更新

每台机器只需 clone 两个仓库一次：

```sh
git clone https://github.com/kitchen-engineer42/hamster ~/hamster-cli
git clone https://github.com/kitchen-engineer42/joharnessburg ~/joharnessburg
```

当你希望新 workspace 使用最新版本时，更新两个干净 clone：

```sh
git -C ~/hamster-cli pull --ff-only
git -C ~/joharnessburg pull --ff-only
```

Hamster v0.3.1 对齐 John v0.5.1。

## 创建 workspace

建立空工作目录，然后选择 provider。默认值是 `both`。

```sh
mkdir -p ~/my-template-build
cd ~/my-template-build

# 两个 provider（默认）
~/hamster-cli/bootstrap_hamster.sh
# 等价于：~/hamster-cli/bootstrap_hamster.sh --provider both

# 仅 Claude Code
~/hamster-cli/bootstrap_hamster.sh --provider claude

# 仅 Codex
~/hamster-cli/bootstrap_hamster.sh --provider codex
```

每种选择都会安装 `HAMSTER.md`。Claude 会得到 `CLAUDE.md` 和 `.claude/skills/`；Codex 会得到 `AGENTS.md` 和 `.agents/skills/`。已有文件和 skill 目录会被跳过，绝不覆盖。

## 启动与第一条 prompt

启动你选择的 provider：

```sh
cd ~/my-template-build
claude
```

```sh
cd ~/my-template-build
codex
```

两个运行时使用同一条首个 prompt：

> John 位于 `~/joharnessburg`。输入位于 `~/template-inputs/some-folder/`。模板名：`slides-from-physics-textbooks`。请构建一个模板，让应用把物理教材章节转化为交互式幻灯片。

## 工作流与产出

Hamster 采用同一个 provider-neutral 撰写循环：

1. **Orient** —— 加载 `HAMSTER.md` 和 `hamster-orientation`。
2. **Design** —— 对输入分类，并确定知识格式、知识 schema、app mechanism 和 build pipeline。
3. **Fork** —— 把干净的 John 源 clone 到 `forks/<name>/`。
4. **Package** —— 用明确的模板版本和精确 John pin，把受支持的 fork 变更转化到 `templates/<name>/`。
5. **Validate** —— 在原子发布前检查语法与契约、重定位、规范 `apply.sh`、真实应用和项目初始化。

仅供 builder 使用的 provenance 保存在 `forks/<name>/.hamster/package_summary.json`；只分发 `templates/<name>/`。

Claude 用户应用模板后，用 `claude --plugin-dir` 启动合并插件。Codex 用户应用同一个模板，再通过 John 的 `codex-template-activation` skill 在项目本地激活合并插件，在该项目禁用 vanilla John，审阅 hooks，然后重启。

## 快照与更新模型

Bootstrapped workspace 是**不覆盖的快照**。更新 Hamster 或 John clone 会改变新 workspace 得到的内容；不会修改已有 build。

需要可复现性时，让活跃 build 保持固定。要采用新的共享指导，请明确创建一个新 workspace，并针对新的 John 版本重新构建。Hamster 不提供破坏性 refresh 或自动 migration 参数。

## 示例与结构

`examples/slides-from-textbook/` 和 `examples/doc-verification/` 是完整的双 provider 格式演示。两者版本均为 v0.1.3，并精确固定 John v0.5.1。

```text
HAMSTER.md                         共享 session guide
CLAUDE.md / AGENTS.md             轻量 provider adapters
bootstrap_hamster.sh              不覆盖的 workspace installer
skills/hamster-*/                 撰写方法论与严格工具
examples/                         双 provider John 模板
tests/                            bootstrap、packaging、重定位和应用测试
VERSION                           Hamster release version
```

## 版本与许可

当前版本：**0.3.1**。Hamster 使用 MIT 许可证；见 [`LICENSE`](LICENSE)。
