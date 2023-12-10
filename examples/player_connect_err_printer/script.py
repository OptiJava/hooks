from mcdreforged.api.all import *

# hooks在执行本脚本时会自动提前声明info、server这几个实例，所以你可以忽略IDE提示的"未解析的引用"，本脚本在实际执行时是没有问题的
# 使用/开发之前一定要仔细阅读仓库根路径下的README.md ！！！！！！
if info.content.__contains__('lost connection: ') \
        and not info.content.endswith('Disconnected') \
        and not info.content.endswith('Killed'):
    server.tell('@a', RTextList(
        RText('检测到玩家非正常退出：', color=RColor.red),
        RText(info.content, color=RColor.yellow).c(RAction.copy_to_clipboard, info.content).h('点击复制到剪贴板'),
    ))