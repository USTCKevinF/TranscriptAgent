# 采访稿件整理工具

这是一个基于大语言模型的采访稿智能整理工具,可以自动清理口语化表达、语气词,并对采访内容进行优化润色,输出规范的采访稿件。

## 主要功能

- 自动删除口语中的语气词、填充词(如"那个"、"就是"、"嗯"等)
- 优化表达方式,使内容更易理解
- 将口语化表达改写成轻松活泼的书面语
- 保持说话人的语气特点
- 多线程并行处理,提高处理效率
- 自动分段处理长文本
- 支持多轮迭代优化

## 使用方法

1. 安装依赖:

```bash
pip install openai yaml tiktoken
```

2. 配置文件:
   复制 `config.yaml.example` 为 `config.yaml`,并填写以下配置:

```yaml
api_key: "你的OpenAI API密钥"

base_url: "API基础URL"

model: "gpt-4" # 使用的模型

interviewee_name: "被采访者姓名"

interviewee_introduction: "被采访者简介"

input_file: "input/interview.txt" # 输入文件路径

output_file: "output/revised.txt" # 输出文件路径

temperature: 0.7 # 温度参数

revise_iteration: 1 # 迭代优化次数

chunk_size: 5000 # 分段大小
```



## 工作流程

1. 读取原始采访文本（由腾讯会议 智能优化版文档导出）
2. 预处理文本(移除时间戳、统一说话人名称等)
3. 按chunk_size大小分段处理
4. 多线程并行处理每个文本段
5. 对每段文本进行多轮迭代优化:
   - 初次润色
   - 检查内容差异
   - 补充遗漏信息
6. 合并处理结果并输出

## 文件说明

- `main.py`: 主程序文件
- `prompts.yaml`: 提示词配置文件
- `config.yaml`: 配置文件
- `config.yaml.example`: 配置文件示例

## 注意事项

- 确保输入文本格式为: "说话人: 内容"
- 大文本建议适当调整chunk_size大小
- 可根据需要调整revise_iteration参数控制优化次数
- 请确保API密钥配置正确

## 许可证

MIT License