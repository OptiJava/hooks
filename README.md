# hooks

> 为各种脚本提供了一些触发器和接口，让mcdr自动根据某些条件触发脚本，更方便的使用全自动化管理脚本去做各种事情

追求服务器管理、维护全自动化！

**_目前此插件部分功能无法在Windows上使用！如果在非posix操作系统上使用此插件，会在加载插件时收到警告。_**



## 目的

有时，我们想要使用shell脚本管理服务器，但是不方便去让mc服务器全自动触发这些shell脚本，这个插件就是为了能更方便的使用各种脚本全自动维护/管理服务器

他可以为shell脚本提供一系列的“钩子”（也就是hooks），还有许多接口，让脚本的可定制化程度更高

## 使用方法

### 几个概念

1.`Task`（任务）
\
Task就是一个任务，任务是可执行的（可被手动执行也可以被自动执行）。目前支持三个任务类型（task_type）`shell_command`（shell指令） `server_command`（mc指令） `mcdr_command`（mcdr命令）

2.`Hooks`（钩子）
\
插件内置了很多“钩子”，Hook是可以被触发的，一个Task可以被挂载（mount）到一个或多个Hooks下，也可以从一个hook中卸载（unmount）。一旦一个hook被触发，其下被挂载的所有Task全部会被执行（异步）。例如`on_server_started`会在mc服务端完全启动成功时被触发，其下挂载的所有任务会被异步执行

3.`Script`（脚本）
\
这里说的脚本是这个插件可以识别的yaml格式的脚本文件，脚本应放在`config/hooks/scripts`文件夹中。在插件被加载时或`!!hooks reload`指令被执行时，那个文件夹及子文件夹里面的所有脚本文件全部会被加载（注意是加载不是应用）

4.`Apply`（应用）
\
Apply和加载有区别，Apply是指：**插件创建Task、挂载Task的操作**，加载在前，应用在后

手动应用就是你自己打指令`!!hooks create ...`之类的，脚本自动应用就是插件加载脚本后自动解析脚本，然后根据脚本内容自动创建task，挂载之类的

### 应用方式

分为两种：手动应用和脚本自动应用，先介绍手动应用

#### 手动应用

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

`!!hooks unmount <task> <hook>`

- 从一个hook卸载一个task

**注意：每一次!!hooks reload或者重载插件都会将所有task以及挂载信息删除，然后重新根据脚本进行应用，也就是说你手动应用的是留不住的，重载就没了，强烈建议写yaml脚本**

#### 脚本自动应用

首先要编写脚本，示例：
``````
tasks:
  motd:  # 声明一个task（其实这个你可以随便写，task的名字取决于name）
    name: motd  # 声明task的名字，别有空格
    task_type: shell_command  # 任务类型
    command: date   # 要执行的指令
    hooks:   # 要挂载到的hook，必须是数组
      - on_server_started
``````

将其命名为`<脚本名字>.yaml`，并且放到`config/hooks/scripts`文件夹或子文件夹中

### 其他指令

`!!hooks list mount`
- 显示挂载情况

`!!hooks list task`
- 显示所有被创建的task

`!!hooks run <task> <env>`
- 手动执行任务（跟挂没挂载没关系）
- `<task>` 任务名
- `<env>` 参数列表（具体用法往下看），必须用`json`格式

## 高级用法

### 获取“参数”

有时，光有hook还不够，我想在执行脚本时获取服务器的信息，怎么获取？ ~~怎么感觉越来越像github actions了~~

插件在触发这些脚本时，自己是知道一些包含着服务器信息的对象的，关键是如何将对象中的信息传递给脚本，不同的task_type有不同的传递方式

`shell_command`：
- 插件会把想要传递的信息放到环境变量中，假设你想执行`echo abababab`，实际上插件执行的命令是：`export xxx=xxx && export xxxx=xxxx && ... && echo abababab`
- 注意：不同的hook传递不同类型的对象，比如`on_server_stopped`传递`server`和`return_code`两个对象，on_info传递`server`和`info`两个对象。插件会把每一个对象里面的每一个属性（函数除外）都放到各个环境变量中（除非这个对象是个基本类型，例如`on_server_stopped`的`return_code`对象），即使这个属性是一个非基本类型也会被转成str放进环境变量
- 假设你想要访问`server`中的`mcdr`属性，那么在shell脚本中，你应该使用`$server_mcdr`访问这个属性，即`$对象名_属性名`，注意：通过这种方式无法访问函数，就算这个函数是一个无参且返回基本类型的函数也不行

`server_command`：
- 注意：不同的hook传递不同类型的对象，不同的对象有不同的属性
- 插件在执行你指定的命令前，会对指令进行处理，例如`{$server_mcdr}`会被替换为`True`，跟shell的访问方法类似，仍然是`$对象名_属性名`访问属性，只不过多了个大括号

`mcdr_command`：
- 注意：不同的hook传递不同类型的对象
- 跟`server_command`访问方法完全一样 ~~连代码都一样~~

### “获取”函数值

如果你看了mcdr源代码，你会发现，其实很多信息是要调用函数才可以获取到的，只能访问属性还不够，例如`PluginServerInterface.is_server_running()`，那怎样才能在脚本中调用无参函数并获取返回值呢？

我想到的~~坏~~方法是这样的：首先在执行脚本前，先把一些关键的、常用的无参函数调用一遍，并且把他们的值缓存起来，然后把这些值绑定进入那个对象，绑定的这个属性就叫做`func_`+`函数的名字`，这样就成功的实现了函数->属性的转变。我绑定进去的这些属性会随着这个对象的其他属性一起被“拆包”然后放入对应的各个环境变量中，供脚本访问。

以shell格式脚本为例：`PluginServerInterface`中有函数`is_server_running()`，你想要访问他，就需要使用`$server_func_is_server_running`访问

**注意：并不是每一个对象的每一个函数的值都可以在脚本中使用**

### 所有可以在脚本中访问的属性列表

**_TODO_**  ~~（其实就是懒）~~

粗略判定方法：

看插件源码，找到__init__.py，翻到最后，你会看到类似
``````
def on_mcdr_start(server: PluginServerInterface):
    trigger_hooks(Hooks.on_mcdr_started, server, {'server': process_arg_server(server)})
``````
这样的代码，先看函数名`on_mcdr_start`，就能大致判断这块代码负责触发`on_mcdr_started`，再看`trigger_hooks(...)`，括号里面的最后一个参数是一个`dict`，只有一个`server`键对值，说明最终脚本可以访问到的参数全都在`PluginServerInterface`类中，然后看就完了（（（（逃
