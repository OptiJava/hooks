# hooks

> 为shell脚本、mc指令、mcdr指令提供了一些触发器和接口，让mcdr自动根据某些条件触发脚本，更方便的使用全自动化管理脚本去做各种事情

## 目的

有时，我们想要使用shell脚本管理服务器，但是不方便去让mc服务器全自动触发这些shell脚本，这个插件就是为了能更方便的使用各种脚本全自动维护/管理服务器

他可以为shell脚本提供一系列的“钩子”（也就是hooks），还有许多接口，让脚本的可定制化程度更高

举一个不太恰当的例子，我的服务器磁盘空间少，我想每次服务器回档之后，都把qb自动生成的那个overwrite给删除掉，怎么办？（假设overwrite文件夹位于`~/server/qb_multi/overwrite`）

1.在`~/scripts/`下创建一个shell脚本`clean_overwrite.sh`

2.脚本里面写上
```
rm -rf ~/server/qb_multi/overwrite
echo 成功删除overwrite！
```

3.安装此插件

4.创建一个Task 名称：`clean_overwrite`  类型：`shell_command`  执行的命令：`~/scripts/clean_overwrite.sh`
`!!hooks create clean_overwrite shell_command ~/scripts/clean_overwrite.sh`

5.将`clean_overwrite`任务 挂载到`on_server_starting`（也就是服务器启动时执行的钩子）（每当一个“钩子”（也就是hooks）被触发时，其下挂载的所有任务将被依次执行，执行顺序不能保证；一个任务可以被挂载到多个hooks，也可以不挂载（也就是不自动运行））
`!!hooks mount clean_overwrite on_server_starting`

6.下次启动服务器时你就会发现，脚本被运行了！控制台显示：`成功清除overwrite！`（如果不出意外的话）

## 使用方法

`!!hooks create <name> <task_type> <command>` 

- 创建一个任务

- `name` 就是这个任务的名字
- `task_type` 就是你要执行的脚本的类型，有以下几种选择：`shell_command`（shell脚本）、`server_command`（mc指令）、`mcdr_command`（mcdr指令）
- `command` 要执行的指令，例如`./cleanup.sh`或`echo awa`或`say hello`或`!!qb make auto_backup`（写啥指令取决于你的任务类型，注意别写错了）

`!!hooks mount <task> <hook>`

- `task` 要挂载的命令的名字
- `hook` 要挂载到的钩子
- 所有的合法hooks：（都是字面意思，很好理解）
```
    on_plugin_loaded（hooks这个插件被加载时）
    on_plugin_unloaded（hooks这个插件被卸载时）
    
    on_server_starting（mc服务器正在启动）
    on_server_started（mc服务器启动成功）
    on_server_stopped（mc服务器彻底关闭）
    on_server_crashed（即服务器返回代码非0时触发，理论上服务器同一次关闭只会触发on_server_crashed和on_server_stopped中的其中一个）
    
    on_mcdr_started（mcdr被启动）
    on_mcdr_stopped（mcdr被停止）
    
    on_player_joined
    on_player_left
    
    on_info（控制台info时，就是控制台输出日志时）
    on_user_info（就是有玩家或者控制台发送了消息或mcdr指令）（这俩具体去看mcdr文档）
```

## 高级用法

### 获取“参数”

有时，光有触发器还不够，我想在执行脚本时获取一些服务器的信息，怎么获取？ ~~怎么感觉越来越像github actions了~~

插件在触发这些脚本时，自己是知道一些包含着服务器信息的对象的，关键是如何将对象中的信息传递给脚本，不同的task_type有不同的传递方式

shell_command：
- 插件会把想要传递的信息放到环境变量中，假设你想执行`echo abababab`，实际上插件执行的命令是：`export xxx=xxx && export xxxx=xxxx && ... && echo abababab`
- 注意：不同的hook传递不同类型的对象，比如`on_server_stopped`传递`server`和`return_code`两个对象，on_info传递`server`和`info`两个对象。插件会把每一个对象里面的每一个属性（函数除外）都放到各个环境变量中（除非这个对象是个基本类型，例如`on_server_stopped`的`return_code`对象），即使这个属性是一个非基本类型也会被转成str放进环境变量
- 假设你想要访问`server`中的`mcdr`属性，那么在shell脚本中，你应该使用`$server_mcdr`访问这个属性，即`$对象名_属性名`，注意：通过这种方式无法访问函数，就算这个函数是一个无参且返回基本类型的函数也不行

server_command：
- 注意：不同的hook传递不同类型的对象，不同的对象有不同的属性
- 插件在执行你指定的命令前，会对指令进行处理，例如`{$server_mcdr}`会被替换为`True`，跟shell的访问方法类似，仍然是`$对象名_属性名`访问属性，只不过多了个大括号

mcdr_command：
- 注意：不同的hook传递不同类型的对象
- 跟`server_command`访问方法完全一样 ~~连代码都一样~~

### “获取”函数值

如果你看了mcdr源代码，你会发现，其实很多信息是要调用函数才可以获取到的，只能访问属性还不够，例如`PluginServerInterface.is_server_running()`，那怎样才能在脚本中调用无参函数并获取返回值呢？

我想到的~~坏~~方法是这样的：首先在执行脚本前，先把一些关键的、常用的无参函数调用一遍，并且把他们的值缓存起来，然后把这些值绑定进入那个对象，绑定的这个属性就叫做`func_`+`函数的名字`，这样就成功的实现了函数->属性的转变。我绑定进去的这些属性会随着这个对象的其他属性一起被“拆包”然后放入对应的各个环境变量中，供脚本访问。

以shell格式脚本为例：`PluginServerInterface`中有函数`is_server_running()`，你想要访问他，就需要使用`$server_func_is_server_running`访问

**注意：并不是每一个对象的每一个函数的值都可以在脚本中使用**

### 所有可以在脚本中访问的属性列表

TODO
