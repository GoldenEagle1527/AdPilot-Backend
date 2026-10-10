# OC投放中台

### 【需求背景】

目前杭州用的投放系统是买断后本地化部署的，但是存在随时被收回使用权的可能，所以产研端需要复刻一套功能相似的投放系统，避免投流业务断档

### 【外部接口地址】

常读：[https://www.changdupingtai.com/sale/open-api-document?interface\_name=GetAwemeSeriesListOpen](https://www.changdupingtai.com/sale/open-api-document?interface_name=GetAwemeSeriesListOpen)

*   常读是内部接口文档，需要用自己手机号注册常读，然后 $\color{#0089FF}{@王旭}$ 拉进企业组织
    
*   常读开发者账户等待商务提供中
    

巨量：[https://open.oceanengine.com/labels/7/docs/1696710599092236?origin=left\_nav](https://open.oceanengine.com/labels/7/docs/1696710599092236?origin=left_nav)

*   巨量接口文档可以直接访问
    

### 【投放系统框架及需求推进计划】

| **一级菜单** | **二级菜单** | **三级菜单** | **计划** | 负责人-需求地址 |
| --- | --- | --- | --- | --- |
| 系统管理 | 组织管理 | 部门管理 | 9.19已出需求 | 王旭 |
|  | 权限管理 | 角色管理 |
|  |  | 用户管理 |
|  |  | 权限角色查询 |
| 素材管理 | 视频 |  | 9.19已出需求 |
|  | 标题 |  |
|  | 漫剧流转剧库 |  |
| 智能投放 | 巨量广告 | 账户 | 9.30出需求 | 王旭 |
|  |  | 项目 |
|  |  | 广告 |
|  |  | 素材 |
|  |  | 全域项目 |
|  | 漫剧标准投放 | (免费)端原生投放任务 | 9.23出需求 | 刘俊良[《oc投放-智能投放-漫剧标准投放.adoc》](https://alidocs.dingtalk.com/document/edit?docKey=WgZOZA5DKdZPyqLX&dentryKey=1V7Nqbbjtag3qoEQ&type=d) |
|  |  | (免费)端原生模板管理 |
|  |  | (付费)端原生投放任务 |
|  |  | (付费)端原生模板管理 |
|  |  | (免费)端原生自动投放 |
|  |  | (付费)端原生自动投放 |
|  |  | ~~漫剧同素材投放任务（本期不做）~~ |
|  |  | ~~自动剪辑投放任务（本期不做）~~ |
|  | 漫剧全域投放 | 端原生投放任务 | 9.22出需求 | 王旭 |
|  |  | 端原生自动化投放 |
|  | 全域模板管理 | 全域模板管理 |
|  |  | 抖音号分配 |
|  | 账户管理 | 广告主管理 | 9.22出需求 | 王旭 |
|  |  | 授权组织 |
|  |  | 投放主体 |
|  |  | 抖音号管理 |
|  |  | 全域抖音号分配 |
|  |  | 商品库管理 |
|  | 标准自动投放策略 | 自动关停 | 9.22出需求 | 刘俊良[《oc投放-智能投放-标准自动投放策略.adoc》](https://alidocs.dingtalk.com/document/edit?docKey=QvjnA3JNGeX48OXo&dentryKey=WlVnExjBU4yrYgNA&type=d) |
|  |  | 小程序自动投放策略 |
|  |  | 端原生自动投放策略 |
|  |  | 端原生投手补广告 |
|  |  | 端原生补广告规则 |
|  |  | 端原生补广告日志 |
|  |  | (免费)漫剧端原生机器人 |
|  |  | (付费)漫剧端原生机器人 |
|  | 全域自动投放策略 | 自动投放策略 | 9.22出需求 | 刘俊良<br>[《oc投放-智能投放-全域自动投放策略.adoc》](https://alidocs.dingtalk.com/document/edit?docKey=NpQlK57oEErejqDv&dentryKey=JqY7qvgbij7eB1ya&type=d) |
|  |  | 漫剧机器人 |
|  | 三方剧场 | 平台列表 | 9.21已出需求 | 王旭 |
|  |  | 平台管理 |
|  |  | 应用列表 |
|  |  | 端原生推广链 |
|  |  | 番茄推广链接同步 |
|  |  | ~~机器人剪辑~~ | ~~不用做~~ |  |
| 数据报表 | 漫剧报表 | R1IAP | 10.10出需求 | 刘俊良<br>[《oc投放-数据报表-漫剧全域报表.adoc》](https://alidocs.dingtalk.com/document/edit?docKey=AJdl659kgdLoKOke&dentryKey=ajZX27ZyTPvw2q79&type=d)[《oc投放-数据报表-漫剧报表.adoc》](https://alidocs.dingtalk.com/document/edit?docKey=ZWGl05KkpozQQn34&dentryKey=gvmEo3mNU3lKWBqX&type=d) |
|  |  | IAP项目 |
|  |  | IAP广告 |
|  |  | R1LAA |
|  |  | IAA项目 |
|  |  | IAA广告 |
|  | 漫剧全域报表 | 短剧报表 |
|  |  | 投手报表 |
|  |  | 组报表 |
|  | 素材报表 | 素材消耗 |  | 王旭 |
|  |  | 剪辑师消耗 |
|  |  | 素材报表 |
|  |  | 剪辑师统计 |
|  | 利润报表 | 利润统计概览 |
|  |  | 每日利润统计 |
|  |  | 投手利润统计 |
|  |  | 组利润统计 |
|  | 首页 |  |  | 刘俊良[《oc投放-首页.adoc》](https://alidocs.dingtalk.com/document/edit?docKey=mxPOG5vk0Q3pMnKa&dentryKey=oaAjJWL3sVWJeXAr&type=d) |

### 【投放系统组织结构】

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/14454321-f007-4b7f-b2c9-8106b5754d75.png)

### 【需求内容】

**前置说明：**

*   文档中红色文字内容是本次需求中待定功能（本次预留字段，后续扒下个板块逻辑时，补充字段间的关联逻辑）
    
*   文档中灰色文字内容是目前不需要做的功能
    

#### 1、系统管理

:::
**系统管理板块简述**

使用人：管理员

作用：配置人员账号权限，通过人员部门以及人员角色进行分组式、批量化管理
:::

##### 1.1、角色管理

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/2c37bc4d-35d9-4676-b63f-f156addadab4.png) |
| 查询条件 | 角色名称 | 模糊搜索 |
|  | 状态 | 1、下拉单选，枚举：启用、停用<br>2、默认查询全部状态 |
| 列表字段 | 角色id | 研发自己定义，唯一即可 |
|  | 角色名称 |  |
|  | 备注 |  |
|  | 状态 | 1、枚举：启用、停用<br>2、新建的账号默认为启用状态<br>3、列表中可直接点击【启停开关】开启或关闭<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/3bdecf24-751b-4f37-b4d3-62d432ae820f.png) |
|  | 已分配用户 | 关联用户管理页面配置的用户角色数据 |
|  | 已分配部门 | 关联部门管理页面配置的部门角色角色 |
|  | 创建时间 | 精确到秒 |
|  | 更新时间 | 精确到秒 |
|  | 更新人 | 用户登录账号（因为账号昵称可以改） |
|  | 操作 | 【修改】、【分配权限】<br>1、可以修改\*角色名称以及备注这2个字段<br>2、分配权限：<br>*   业务领域：<br>    <br>    *   下拉单选<br>        <br>    *   枚举：推广域、素材域、资产域、报表域<br>        <br>    *   业务领域的作用是：选择后可以快捷圈出对应页面的属性结构（不用再慢评属性结构中找对应页面，省事儿）<br>        <br>        *   推广域：包含智能投放下除了账户管理外的所有页面<br>            <br>        *   素材域名：包含素材管理下的所有页面<br>            <br>        *   资产域：智能投放-账户管理下的所有页面<br>            <br>        *   报表域名：包含总览和数据报表下的所有页面<br>            <br>*   树形结构展示系统所有页面，可勾选角色可拥有的页面/按钮权限<br>    <br>*   ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/14cde318-cdbe-408c-b798-ec9b74b38ce4.png) |
| 其他说明 | 新增 | 点击左上角【新增】按钮，弹窗页配置2个字段：\*角色名称、备注<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/f7f0f655-d54f-481c-870b-d37cab445bdb.png) |

##### 1.2、部门管理

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/91812d0b-2c33-4af9-9f89-7cd8255e451e.png) |
| 查询条件 | 部门名称 | 模糊查询 |
|  | 部门id | 精确查询 |
|  | 状态 | 1、下拉单选，枚举：启用、停用<br>2、默认查询全部状态 |
| 列表字段 | 批量勾选框 | 1、勾选部门后，可以点击列表左上方的【添加部门标签】按钮，给这个部门打上标签（用于快速识别这个部门的分工）<br>2、点击【添加部门标签】，弹窗页面只展示1个字段【部门标签】，下拉多选，枚举：投放部、投放组、素材部、素材组<br>3、保存标签后，在列表中的标签字段展示这个标签<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/911e67f6-daa5-458e-a704-93af695cadfb.png) |
|  | 部门名称 | 树形菜单展示，可在每一级部门下添加子部门（点击部门对应操作栏的【添加子部门】按钮即可） |
|  | 部门id | 研发自己定义，保证部门id唯一性即可 |
|  | 状态 | 1、枚举：启用、停用<br>2、新建的账号默认为启用状态<br>3、列表中可直接点击【启停开关】开启或关闭<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/3bdecf24-751b-4f37-b4d3-62d432ae820f.png) |
|  | 部门角色 | 1、可点击操作栏的【分配角色】按钮，给部门分配角色<br>2、部门可分配多个角色，权限为角色的并集<br>3、如果单个用户没有配置角色权限，默认使用部门角色（下文会讲到） |
|  | 标签 | 列表中可直接点击标签叉号，删掉部门标签![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/09b922ef-d80a-418a-bb31-488ef284fac2.png) |
|  | 排序 | 同一级别如果有多个部门，需要根据需要进行排序展示，从上到下按序号正序排列 |
|  | 创建时间 | 精确到秒 |
|  | 操作 | 1、对应4个按钮：【修改】、【添加子部门】、【分配角色】、【删除】<br>2、如果部门下有配置员工，则删除时需要提示，且不能删除（需要把员工挪到其他部门）<br>3、删除页面不展示，但是库中要留存<br>4、分配角色：弹窗页打开下图弹窗页面，可以给当前部门分配角色，可多选，多选后权限为角色的并集<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/352349df-91b8-4f4f-b8d6-96659da8808e.png) |
| 其他说明 | 新增部门 | 列表做商家展示这个按钮，打开的弹窗页面共3个配置字段：<br>1、所属父级：组织架构下拉单选<br>2、部门名称：文本格式<br>3、显示排序：数字格式，根据数字展示在这个父级部门下的排序<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/36dd97f5-5af6-41c2-9aea-3ae56dca9839.png) |

##### 1.3、用户管理

*   左右结构展示页面
    
*   左侧：部门组织架构图（部门单选，选择后部门后，右侧用户列表展示对应部门下的用户）
    
*   右侧用户列表说明如下
    

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b7b16bac-aa70-4e77-8db4-1209b4680874.png) |
| 查询条件 | 用户昵称 | 模糊查询 |
|  | 用户Id | 精确查询 |
|  | 账号 | 精确查询 |
|  | 状态 | 1、下拉单选，枚举：启用、停用<br>2、默认查询全部状态 |
|  | 手机号 | 精确查询 |
| 列表字段 | 批量勾选框 | 1、勾选后，可以给用户打上标签（点击列表左上方的【新增用户标签按钮】）<br>2、点击【新增用户标签按钮】，弹窗页如下图，岗位类别标签下拉多选，标签类型：投手、素材手<br>3、保存后，在用户列表中的标签字段展示所选标签即可<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/a9c08bdb-2c9e-4faa-b1b5-92b78d4c98db.png) |
|  | 用户昵称 |  |
|  | 用户Id |  |
|  | 账号 |  |
|  | 状态 | 1、枚举：启用、停用<br>2、新建的账号默认为启用状态<br>3、列表中可直接点击【启停开关】开启或关闭<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/3bdecf24-751b-4f37-b4d3-62d432ae820f.png) |
|  | 手机号 |  |
|  | 标签 | 列表中可直接点击标签叉号，删掉用户标签![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/551c131f-0ed3-4aff-a47b-6d6546aafeb8.png) |
|  | 部门 |  |
|  | 数据权限 | 数据取自操作栏配置的数据权限 |
|  | 角色 |  |
|  | 创建时间 | 精确到秒 |
|  | 备注 |  |
|  | 操作 | 1、【修改】：基础字段同新增页面，但登录账号不可修改<br>2、【分配角色】：参考下图页面，同一个人的权限，有用户角色权限与部门角色权限，两者权限取并集<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/d5772802-427d-47aa-82ff-2a565e57ffa9.png)<br>3、【分配数据权限】：参考下图，勾选某个部门后，当前用户就有这个部门下所有用户的数据权限，不勾选就只有自己的数据权限<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b08b381c-d70f-431d-af67-644136c8068c.png)<br>4、【重置密码】：弹窗页直接配置新密码/新密码确认字段（这里就不给手机号发送给短信了，非核心功能，本次省开发时间以及成本）<br>5、【删除】：页面删除记录，库中做数据留存 |
| 其他 | 新增用户 | 1、新增页面字段，及必填字段参考下图即可<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/4e1e4eb0-71bd-47c1-9a99-15eae915f173.png) |

---

#### 2、素材管理

:::
**素材管理板块简述**

使用人：素材手（制作人员）

作用：为漫剧制作推广素材（视频格式），给到投手去做推广，为漫剧引流

补充业务说明：引流的用户观看漫剧付费后，oc也可获得一定比例的佣金
:::

##### 2.1、漫剧流转剧库

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/d20ff0b8-a788-44f3-aacc-09400ffab79b.png) |
| 页面逻辑 |  | 1、系统通过官方接口获取抖音旗下常读平台的短剧<br>接口文档：[https://www.changdupingtai.com/sale/open-api-document?interface\_name=GetAwemeSeriesListOpen](https://www.changdupingtai.com/sale/open-api-document?interface_name=GetAwemeSeriesListOpen)<br>2、这个页面不做数据权限管控，所有人都有权从库中找 |
| 名词解释 |  | IAA短剧：免费短剧，靠应用内广告变现<br>IAP短剧：付费短剧，前几集免费，后面付费<br>备注：同一部剧，2种形式会同时存在 |
| 查询条件 | tab切换 | 分多tab展示漫剧库，各tab下呈现的查询条件和列表字段相同（只是作为一个快捷筛选）<br>*   接口返回参数：single\_price>0则为付费 |
|  | 短剧名称 | 模糊查询 |
|  | 预估投放时间 | 日期段查询，左闭右闭 |
|  | 采集时间 | 日期段查询，左闭右闭 |
|  | 发布状态 | 1、下拉单选：未发布、已发布<br>2、默认查询全部 |
|  | 是否当天上架 | 1、下拉单选：是、否<br>2、默认查询全部 |
|  | 部门 | 组织架构下拉单选 |
|  | 集数 | 数字格式，左闭右闭<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/dbe2d46c-5ad6-4e62-b1e2-c694ed832cd0.png) |
| 列表字段 | 封面 | 接口返回参数：thumb\_url |
|  | 短剧名称 | 接口返回参数：book\_name |
|  | 集数 | 接口返回参数：episode\_amount |
|  | 部门 | 如果这部剧在私彩管理-视频中，被投放部下的某个子部门用户制作了投流素材，那就显示对应的这个子部门名称（投放一部或者投放二部） |
|  | 发布状态 | 接口返回参数：publish\_status |
|  | 可投放状态 | 接口返回参数：delivery\_status |
|  | 发布时间 | 接口返回参数：publish\_time |
|  | 预估可投时间 | 接口返回参数：estimate\_publish\_time |
|  | 短剧创建时间 | 接口返回参数：create\_time |
|  | 采集时间 | 我们调接口获取数据的时间 |
|  | 素材 | 素材管理-视频页面，这部剧创建的投流素材（案例系统目前这个字段全部为空值），我们暂时也不展示，因为一部剧可能有几十个视频素材，列表展示会影响整洁度 |
|  | 抖音号 | 接口返回参数：douyin\_nick\_name |
| 其他 | 导出 | 支持将页面查询结果数据，按列表原字段导出excel |
|  | 接口调用频率 | 每10分钟调一次接口，每次查当前时间往后10分钟的数据（接口入参：start\_time+end\_time字段） |

##### 2.2、标题

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/0ee9390a-6796-4b90-9154-5d291643665c.png) |
| 标题逻辑 |  | 配置的标题，会在视频素材上方展示文字（其他页面配置策略时，会引用到这边的标题枚举库） |
| 查询条件 | 分类 | 1、下拉单选：付费标题、通用标题<br>2、默认查询土芹爱吧 |
|  | 标题 | 模糊搜索标题名称 |
|  | 上传者 | 下拉单选上传用户昵称 |
| 列表字段 | id | 研发定义，唯一即可 |
|  | 素材标题 |  |
|  | 分类 |  |
|  | 标题总消耗 | 不做，会放到报表模块 |
|  | 上传者 | 上传人昵称 |
|  | 上传时间 | 精确到秒 |
|  | 操作 | 【修改标题】：参考下图即可<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/2416d733-30e6-4ca1-9b0a-3174e82ce0fd.png)<br>2、【删除素材】：伪删除 |
| 其他 |  | 1、excel批量导入功能暂时不做，目前只有7条标题数据<br>2、批量添加标题页面的字段参考下图即可<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/c4f516f4-269c-432c-aca8-cc95da13576a.png) |

##### 2.3、视频

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/1ca00b60-fa73-4788-815d-93b8e7b186ce.png) |
| 页面逻辑说明 |  | 1、制作人员会在这个页面关联选择漫剧流转库中的短剧，并制作投流视频素材，制作好的素材可以在智能投放板块，被投手用于投放任务<br>2、制作人员会配置素材归属于哪个投手，投手到这个页面后，只能看到归属于自己的素材 |
| 查询条件 | 视频标签 | 下拉单选，支持模糊搜索选择（添加视频素材页面，会自动生成视频标签） |
|  | 视频名称 | 模糊搜索（添加视频素材页面，会自动生成视频名称） |
|  | 视频id | 精准搜索（添加视频素材页面，会自动生成视频id） |
|  | 短剧筛选 | 下拉单选，支持模糊搜索选择（添加视频素材页面，素材关联的短剧） |
|  | 视频星数 | 这个查询字段不用做（逻辑上是查列表中给每个素材手动打的星），但目前没有用过 |
|  | 归属投手 | 下拉单选，支持模糊搜索选择（添加视频素材页面，配置的投手） |
|  | 上传者 | 下拉单选，支持模糊搜索选择（视频素材上传人） |
|  | 视频文件 | 本地上传的视频素材文件名 |
|  | 归属 | 1、下拉单选，枚举：共有、私有<br>2、默认查询所有，对应添加视频素材页面配置的归属 |
|  | 头条素材id | 这个查询字段不用做 |
|  | 是否转化 | 1、下拉单选，枚举：转化、非转化<br>2、判断逻辑：列表中NB素材转化字段值or素材转化字段值，任意一个大于0，即为转化 |
|  | ~~自动转码~~ | ~~中秋版本先不做转码~~ |
| 列表 | 批量勾选框 |  |
|  | 视频信息 | 视频封面+视频名称+视频id，展示样式参考页面图片<br>*   视频封面：取视频素材第一帧画面<br>    <br>*   视频名称：取创建素材页面生成的视频名称<br>    <br>*   视频id：素材创建好后系统自动生成的唯一id |
|  | 视频标签 |  |
|  | NB素材转化 | 不做，放放到报表模块 |
|  | 素材转化 |
|  | 消耗 |
|  | 平均转化成本 |
|  | 是否低效素材 |
|  | 被拒数 |
|  | 上传者 | 上传人昵称 |
|  | 绑定计划数 | 待产品后续扒投放板块逻辑，先预留字段 |
|  | 消耗计划数 |
|  | 视频文件 | 本地上传的视频素材文件名 |
|  | 视频类型 | 数据取自添加素材页面配置的字段值 |
|  | 归属 |
|  | 头条素材id | 这个字段暂时不用做 |
|  | 上传时间 | 精确到秒 |
|  | 转码时间 | 这个字段暂时不用做 |
|  | 操作 | 1、【每日消耗】：点击后跳到到次级报表统计页面（会放到报表模块）<br>2、【素材共享】：参考下图，可以配置将这个素材共享给其他投手投放（下拉多选用户昵称）<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/979ef744-0197-4284-b018-38a934d51339.png)<br>3、【投手归属】：参考下图，可以配置将这个素材归属权配置给多个用户，归属人有权将素材共享给其他人，被共享人只能用不能配置归属人<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/8968e179-2b8c-46a5-8c20-9f7d13b13175.png)<br>4、【删除】：伪删除 |
| 其他 |  | 2、列表左上角【添加高光视频】功能本次不做<br>3、点击【添加视频】按钮，打开下图页面<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b93f0361-aec6-4061-87e3-79d89118280a.png)<br>*   素材名称：自动生成，置灰不可编辑<br>    <br>    *   素材名生成规则：直接取本地上传的视频文件名<br>        <br>*   素材类型：单选（枚举参考上图）<br>    <br>*   素材文件：支持本地上传多个素材（如果传多个素材，那么素材名称需要展示多个，如果表中名称有重复，需要在名称后用递增数字区分）<br>    <br>*   短剧名称：数据源从漫剧流转剧库中选择<br>    <br>    *   下拉单选，模糊搜索<br>        <br>    *   展示的短剧名称=短剧名称(短剧类型)<br>        <br>*   选择平台：目前只有1个番茄<br>    <br>*   素材标签：根据选择的视频自动生成<br>    <br>    *   格式：视频名称+日期<br>        <br>*   归属：<br>    <br>    *   单选，共有、私有<br>        <br>    *   共有：所有投手都可以使用素材投流<br>        <br>    *   私有：需要选择投手归属（也就是下图页面，需要勾选对应投手保存，只有这些投手可以使用这个素材）<br>        <br>    *   ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/d9e96421-4257-4d89-a71a-845e1d39304a.png) |

---

#### 3、智能投放

:::
**智能投放板块简述**

当制作人员在素材管理板块上传好素材后，投放人员可以在智能投放板块配置投放策略，系统会将最终的投放计划与投放素材同步到巨量系统中
:::

##### 3.1、三方剧场

###### 3.1.1、番茄推广链同步

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/55d70929-a1f7-4495-af77-e66f907c7e4c.png) |
| 页面逻辑 |  | 1、系统查常读端原生推广链接口接口，定时获取推广链<br>[常读获取推广链接列表-v2接口](https://www.changdupingtai.com/sale/open-api-document?aweme_user_new_version=true&begin_date=2026-08-21&end_date=2026-09-20&page_index=1&page_size=10&interface_name=GetPromotionListOpenV2)<br>2、接口查询逻辑：<br>*   根据漫剧流转剧库表中，所有漫剧的预估投放时间判断，到点后，自动触发接口查询，获取这部剧的推广链接(入参bookid)<br>    <br>*   获取推广链失败，每隔10秒重试1次，重试5次失败，则停止重试 |
| 查询条件 | 短剧名称 | 模糊搜索 |
|  | 状态 | 1、下拉单选，枚举：初始状态、需要爬虫、成功、失败、爬虫处理中<br>2、默认查询全部<br>备注：这个字段，研发可以根据自己需要来定义状态 |
|  | 执行时间 | 左闭右闭 |
| 列表字段 | 短剧名称 |  |
|  | 采集人 |  |
|  | 付费类型 | iaa，iap |
|  | 短剧类型 |  |
|  | 状态 |  |
|  | 原因 | 常读响应参数：message |
|  | 执行时间 | 精确到秒 |
|  | 完成时间 | 精确到秒 |
| 其他 | 批量采集 | 1、参考下图，输入指定短剧名称后，调常读接口获取推广链，逻辑如下<br>*   短剧：下拉单选漫剧流转剧库中的短剧，常读接口不支持按短剧名称查询推广链，所以这里选择短剧名称后，需要从漫剧流转剧库表获取book\_id，然后带着book\_id去查[常读获取推广链接列表-v2接口](https://www.changdupingtai.com/sale/open-api-document?aweme_user_new_version=true&begin_date=2026-08-21&end_date=2026-09-20&page_index=1&page_size=10&interface_name=GetPromotionListOpenV2)<br>    <br>*   执行时间：精确到秒，按这里输入的执行时间执行调常读接口任务<br>    <br>*   付费类型：<br>    <br>    *   下拉单选：全部、付费、免费，默认选择全部<br>        <br>    *   接口返回参数：media\_config.media\_config\_type<br>        <br>        *   2付费，3免费<br>            <br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/be276ca9-62d9-4cd0-90ae-f3719f912933.png) |

###### 3.1.2、端原生推广链

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b7111714-e78e-4496-a7ff-d656c50554eb.png) |
| 页面逻辑 |  | 所有已获取推广链的短剧，会在这个页面展示（每条推广链1条记录） |
| 查询条件 | 首发时间 | 日期段查询，左闭右闭 |
|  | 剧场 | 下拉单选，枚举从应用列表配置页获取，下文会讲到 |
|  | 剧名 | 下拉搜索单选 |
|  | 启用状态 | 1、下拉单选，枚举：启动、停用<br>2、默认查询全部 |
| 列表字段 | 剧场 | 应用列表配置页数据，下文会讲到 |
|  | 剧名 | 常读接口返回参数：purchase\_panel\_open\_data.book\_name |
|  | 启用状态 |  |
|  | 出价面板 | 常读接口返回参数：delivery.recharge\_template\_name |
|  | 首发时间 | 常读接口返回参数：book\_info.publish\_time |
|  | 推广链 | 常读接口返回参数：promotion\_info.promotion\_url |
|  | 创建时间 | 常读接口返回参数：promotion\_info.create\_time |
|  | 操作 | 1、【编辑】：除了剧名置灰不可编辑外，其他字段都可编辑<br>2、【停用】：状态变更操作 |
| 其他 | 新增 | 1、当系统调接口没能获取推广链后，投手可以人工点击新增按钮输入推广链<br>*   剧名，下拉搜索选择（从漫剧流转剧库中选择）<br>    <br>*   IAA推广链、中额、小额、超小额、超超小额：文本输入框<br>    <br>    *   投手人工从常读后台复制推广链，然后在我们投放中台手动添加 |

###### 3.1.3、应用列表

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/59db93c8-53c9-4c20-825a-71e04929657e.png) |
| 页面逻辑 |  | 这里配置的应用枚举，在创建投放广告页面会用到 |
| 查询条件 | 平台 | 1、下拉单选：鸥溪、番茄<br>2、默认查询全部 |
|  | 剧场类型 | 1、下拉单选：小程序、端原生<br>2、默认查询全部 |
|  | 投放模式 | 1、下拉单选：IAA、IAP<br>2、默认查询全部 |
|  | 剧场风格 | 1、下拉单选：真人剧、漫剧<br>2、默认查询全部 |
|  | 状态 | 1、下拉单选：有效、无效<br>2、默认查询全部 |
| 列表字段 | 平台 | 数据取自新增页面 |
|  | 剧场名称 |
|  | 剧场类型 |
|  | 投放模式 |
|  | 剧场风格 |
|  | 广告来源名称 |
|  | 状态 | 1、列表中支持编辑状态![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/375844dd-3924-4d40-9cd4-988fb90c1dae.png) |
|  | 创建时间 | 精确到秒 |
|  | 更新时间 | 精确到秒 |
| 新增 | 剧场类型 | 1、单选：小程序、端原生，<br>2、目前只做端原生（所以小程序先不让选） |
|  | 平台 | 1、下拉单选，枚举为需求第4点平台列表配置的数据 |
|  | 投放模式 | 多选：IAA、IAP |
|  | 剧场风格 | 单选：真人剧、漫剧 |
|  | 广告来源 | 文本框，人工填写，巨量做广告审核时会用 |
|  | 剧场名称 | 文本框 |

###### 3.1.4、平台列表

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b9f6fae3-167d-4708-86d3-18c96c382b8b.png) |
| 页面逻辑 |  | 1、平台枚举，在应用列表创建时会用到<br>2、平台不能新建，现有2个平台数据默认生成即可 |
| 查询条件 | 平台名称 | 1、下拉单选：鸥溪、番茄<br>2、默认查询全部 |
|  | 启用状态 | 1、下拉单选：启用、禁用<br>2、默认查询全部 |
| 列表字段 | 平台id | 写死<br>1、番茄平台id=1<br>2、鸥溪平台id=22 |
|  | 平台名称 | 番茄、鸥溪 |
|  | 平台码 | 写死<br>1、番茄平台码=1011<br>2、鸥溪平台码=4504 |
|  | 排序 | 就2条数据，随意 |
|  | 启用状态 | 2个默认都启用 |
|  | 小程序 | 不勾选（目前用不到） |
|  | 端原生 | 默认勾选（勾选上，其他页面选择端原生时，就可以用到这个平台） |
|  | 创建时间 | 精确到秒 |
|  | 更新时间 | 精确到秒 |

##### 3.2、账户管理

###### 3.2.1、授权组织

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b504e24a-7154-4daa-a08f-659e95d36b05.png) |
| 页面说明 |  | 1、目前只做巨量，其他tab渠道不做<br>2、不能新增，预设数据 |
| 列表字段 | 账户id | 自研平台认证：1872115109920903<br>三方服务认证：1872115109920903 |
|  | 账户名称 | 深圳发行中心 |
|  | 认证方式 | 自研平台认证，三方服务认证<br>这2个认证方式，点击后跳转到巨量不同的页面 |
|  | 巨量版本 | 升级版组织 |
|  | 状态 | 默认有效 |
| 其他 | 添加三方服务授权 | 点击跳转：[https://open.oceanengine.com/audit/oauth.html?app\_id=1870857293665690&state={%22agentId%22:%221%22}&material\_auth=1&rid=tg29ccnkpzm](https://open.oceanengine.com/audit/oauth.html?app_id=1870857293665690&state={%22agentId%22:%221%22}&material_auth=1&rid=tg29ccnkpzm) |
|  | 添加自研平台授权 | 点击跳转：[https://open.oceanengine.com/audit/oauth.html?app\_id=1870855836080240&state={%22agentId%22:%221%22,%22agency%22:true}&material\_auth=1&rid=c9lb3o12qhm](https://open.oceanengine.com/audit/oauth.html?app_id=1870855836080240&state={%22agentId%22:%221%22,%22agency%22:true}&material_auth=1&rid=c9lb3o12qhm) |

###### 3.2.2、投放主体

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/f081c0c2-20d7-49a1-bfdc-fb591cc9c296.png) |
| 页面说明 |  | 1、目前只做巨量（腾讯和快手的不做）<br>2、投放主体目前是服务商分配好之后，给到我们主体id，然后我们人工新建到系统中<br>3、创建广告投放计划后，计划中引用到的主体，会将这个id通过接口给到巨量 |
| 查询条件 | 主体名称 | 模糊查询 |
|  | 主体id | 精确查询 |
|  | 投放模式 | 下拉单选：全域投放、标准投放<br>默认查询全部 |
|  | 剧场类型 | 剧场类型：小程序、端原生<br>认查询全部 |
| 列表字段 | 主体名称 | 数据取自创建页面 |
|  | 主体id |
|  | 主体简称 |
|  | 投放模式 |
|  | 剧场名称 |
|  | 剧场类型 |
|  | 收费模式 |
|  | 最低出价 |
|  | 最高出价 |
|  | 实际出价 | 本次不做 |
|  | ROI系数 | 数据取自创建页面 |
|  | arpu | 本次不做 |
|  | 归属部门 | 数据取自创建页面 |
|  | 投放账户 |
|  | 是否双出价 |
|  | 出价面板 |
|  | 操作 |  |
| 其他 | 新增 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/5af6d0a7-b11f-4d0a-a557-678e648eb55d.png)<br>*   主体名称：必填，文本格式<br>    <br>*   主体id：必填，数字格式<br>    <br>*   主体简称：非必填，文本格式<br>    <br>*   投放模式：单选，标准投放、全域投放<br>    <br>*   剧场：下拉单选，枚举从三方剧场-应用列表中获取<br>    <br>*   最低价/最高价：必填，数字格式，最大2位小数，控制广告计划中，使用这个主体的出价必须在这个范围内<br>    <br>*   ROI系数数字格式：非必填，数字格式，最大3位小数，控制广告计划中，使用这个主体的ROI<br>    <br>*   归属部门：非必填，下拉单选，配置哪个部门可以用这个主体，不填就都可以用<br>    <br>*   素材账户：必填，用到这个主体的广告计划，计划中的所有素材都会传到配置的这个素材账户中<br>    <br>*   是否双出价：<br>    <br>    *   双出价：出价+roi，抖音会尽量符合这个组合要求投放<br>        <br>    *   单出价：出价，抖音会尽量符合这个出价要求投放 |

###### 3.2.3、广告账户管理

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b246dbea-0bb5-44af-a695-869d041535fe.png) |
| 页面说明 |  | 1、目前只做巨量账户管理（腾讯和快手的不做）<br>2、广告主账户目前是服务商在他们的系统里负责创建，然后通过巨量接口同步到我们系统：[巨量-获取已授权账户接口](https://open.oceanengine.com/labels/7/docs/1696710506574848?origin=left_nav) |
| 查询条件 | 广告主账户 | 模糊查询 |
|  | 广告主id | 精确查询 |
|  | 归属投手 | 下拉单选（数据取自用户管理中，打了投手标签的用户） |
|  | 所属管家id | 下拉单选（目前只有1个：深圳发行中心） |
| 列表字段 | 多选框 |  |
|  | 广告主账户 | [巨量-获取已授权账户接口](https://open.oceanengine.com/labels/7/docs/1696710506574848?origin=left_nav)：advertiser\_name |
|  | 广告主id | [巨量-获取已授权账户接口](https://open.oceanengine.com/labels/7/docs/1696710506574848?origin=left_nav)：advertiser\_id |
|  | 账户可用余额 | [巨量-获取账户余额](https://open.oceanengine.com/labels/12/docs/1783322092364800)：带着授权账户接口出参里的advertiser\_id字段，作为这个接口的advertiser\_id字段值入参，获取account\_valid<br>*   研发测试的时候，可以用这个广告主id去调接口看下结果值，与我们系统里的值做下对比：1873916032590219 |
|  | 归属投手 | 中台自己分配 |
|  | 所属管家 | 默认只有深圳发行中心 |
|  | 所属主体 | [巨量-投放账户信息查询](https://open.oceanengine.com/labels/7/docs/1809915654787136)：adv\_company\_name<br>*   研发测试的时候，用1873916032590219入参查询，看adv\_company\_name结果值是否=番茄漫剧~普通-我花-我家-低调-岁月-苏子-我替-我不-萌宝-重生-杭州瑶添IAA-常规-48-king-免费#2 |
|  | 操作 | 【账号解绑】：如果这个账号下有正在投放中的广告，则给出提示，不让解绑（提示广告计划名称） |
| 其他 | 分配 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/600451c7-a6c9-40e7-8c46-6072eb77ffc9.png)<br>1、可以给投手分配投放账户（投手=用户管理页面，打了投手标签的用户）<br>2、同一个账号只能分配给1个投手使用，1个投手可以分配多个投放账户 |
|  |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/0f64889c-ff5b-42a4-afae-052e714fa014.png)<br>支持批量绑定 |
|  |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/03c88b42-b1b8-4cc0-81a6-44ef3fec2dbe.png)<br>支持批量改广告主名字 |
|  |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/829e12dc-a47a-442b-b656-dfc3477a3e85.png)<br>支持exel导入解绑、excel导入解绑 |

###### 3.2.4、抖音号管理

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b7b8c78a-e512-45e4-bbc0-d0c55579e8b0.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/dc867bed-6671-41e7-8c61-60fd28f7e816.png) |
| 页面说明 |  | 1、抖音号可以分配给投手<br>2、抖音号的作用：广告投放计划上线后，巨量除了用自身平台流量投放广告，还会基于我们配置的抖音号自然访问流量进行广告投放，我们抖音号流量投放的广告，获客成本非常低（算法在巨量，我们可以通过报表查看数据）<br>3、抖音号分配，分全域投与标准投放两种，可以在这两种投放模式中使用对应配置的抖音号 |
| 全域投放查询条件 | 抖音号 | 精确查询 |
|  | 抖音号名称 | 模糊查询 |
|  | 部门 | 下拉单选 |
| 全域投放列表字段 | 抖音号Id | 1、数据取自创建页面<br>2、状态可以在页面中直接修改（如果有正在投放中的广告用到这这个抖音号，则不能从开启状态变更为关闭） |
|  | 抖音号名称 |
|  | 状态 |
|  | 部门 |  |
|  | 部门负责人 |
|  | 创建时间 | 精确到秒 |
|  | 操作 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/4dd2fa54-e6cc-43e4-8c08-b70e052e6dcd.png)<br>【分配】：参考上图，可以直接分配给投手<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/7adad4a8-13ad-4633-8458-739dd8c68710.png)<br>【编辑】：参考上图，这个页面与新增页面一致<br>【回收】：点击后给出弹窗确认，确认后取消抖音号与部门负责人的关联（如果有正在关联的投放计划，则不能回收，并给出提示）<br>【删除】：点击后给出弹窗确认，确认后逻辑删除（如果有正在关联的投放计划，则不能删除，并给出提示） |
| 其他 | 标准投放 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/73dc6afc-ce8d-4c1d-8a3f-bbfba8fe5a17.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/04f35495-5bc2-4a15-8f93-dbfe59662b54.png)<br>标准投放页面参考上图即可，标准投放的抖音号，是所有投手共用，所以只需要添加即可，不需要分配投手 |

###### 3.2.5、商品库管理

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/0d7d8105-5273-4a42-bd11-84e09236d0cc.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/751a0c5b-5ef1-4cfb-89a3-7102725ef900.png)· |
| 页面说明 |  | 1、商品库的作用：广告投放计划中，所关联的短剧，在配置好后方后，会调巨量接口将短剧文件上传巨量商品库<br>2、如果商品库没有分配投手，默认所有投手的短剧源文件都上传到这个商品库，如果某个商品库分类的投手，那么这个投手的短剧优先上传这个商品库 |
| 查询条件 | 商品库 | 模糊查询 |
|  | 商品库类型 | 1、下拉单选：小说库、视频库<br>2、默认查询全部 |
|  | 归属组织 | 下拉单选，目前只有深圳发行中心 |
| 列表字段 | 商品库 | 显示格式：库名(库Id) |
|  | 商品库类型 |  |
|  | 归属组织 | 目前只有深圳发行中心 |
|  | 投手 |  |
|  | 默认库 | 默认是 |
|  | 操作 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/6d8038c1-ea54-4bd7-a35d-18c86a313530.png)<br>【分配投手】：下拉多选对应投手即可<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/bbd6c502-6b4f-478c-b244-8977ac9afa26.png)<br>【编辑】：与新增页面相同（所有字段必填）<br>【删除】：逻辑删除，当前分配了投手、或者已上传过短剧的库不能删除（删除时给出提示） |

---

##### 3.3、全域模版管理

:::
**全域模板管理说明**

作用：减少配置工作量，将全域投放插件化，通用配置功能放到模板中配置，全域投放广告创建时，直接一键引用模板即可

备注：目前中台没有建国任何模版，所有的模板都是服务商创建，并同步到中台里给投手使用
:::

###### 3.3.1、全域模板配置

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/e36aebb0-5f35-4f34-894f-450a1190a26d.png) |
| 页面逻辑 |  | 这个页面的配置，在正式创建广告投放时，中台负责将字段将参数传给巨量，实际使用是巨量那边的事情（所以这些配置字段具体做什么用的，后续可以慢慢了解，当前只需要做传值） |
| 列表字段 | 模板id | 从服务商那边同步过来的id是3位数，我们id只要能保持唯一即可，研发自己定义 |
|  | 其他列表字段 | 模板名称、投手归属、主体信息、投放变现模式、项目预算、ROI系数、AIGC同态创建、标题选择模式<br>*   这些字段从创建页面的配置中获取展示 |
|  | 创建时间 | 精确到秒 |
|  | 更新时间 |
|  | 操作 | 【编辑】<br>【删除】 |
| 创建页面 | 基础信息 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/db5ed17f-9e53-4840-9c69-99d15a430f06.png)<br>*   模板名称：文本框<br>    <br>*   主体信息：下拉单选，对应投放主体页面模式为全域投放的主体 |
|  | 项目信息 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/149d7bf5-f1d7-4c1a-8a0b-8d473359497a.png)<br>配置字段参考上图 |
|  | 项目排期与预算 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/d9bbe250-ef19-4b18-b5c4-62eda128651e.png)<br>配置字段参考上图 |
|  | 产品信息 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/f912e508-86c7-440e-9611-c9f97e92eeb8.png)<br>配置字段参考上图 |

###### 3.3.2、模板抖音号分配

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/e27b4ed0-be9c-4fbb-a1f2-3d8a77338404.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/95742874-250c-4f9d-b37b-553cf7b11ff5.png) |
| 页面逻辑 |  | 1、当管理员配置好模板后，所有投手的这个页面都会展示出这个模板（模板全员投手通用），但是每个投手可以配置自己的那个抖音号可以用这个模板<br>2、示例：截图中，程浩2配置了2个抖音号关联这个模板，那么程浩2在创建广告投放计划时，如果选择了这个模板，这2个抖音号可以配置具体的投放账户（参考下图）<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/1d3f7b40-18cd-47e1-a506-9eb37818a631.png) |
| 列表字段 |  | 模板id、模板名称、主体信息、抖音号、投放变现模式、项目预算、ROI系数、AIGC动态创意、标题选择模式、创建时间、更新时间、操作（分配抖音号） |

---

##### 3.4、漫剧全域投放

:::
**漫剧全域投放**

作用：基于上述所有基础配置项，创建全域投放任务（以及根据策略自动化创建全域投放任务）

名词解释：全域投放、标准投放从系统配置层面来看，这2种投放区别如下

区别1：

全域：创建一部剧的投放计划，如果计划中只使用了1个抖音号，那么这个投放计划最多使用1个投放账户，投放账户与抖音号是一一对应关系（如果用了多个抖音号，那么投放账户也可以使用多个，但数量必须相等）

标准：创建一部剧的投放计划，只能使用1个抖音号，但是投放账户没有数量限制

区别2：

全域投放：一部剧，在一个抖音号中，只能有1个广告投放计划

标准投放：一部剧，在一个抖音号中，只能有N个广告投放计划
:::

###### 3.4.1、端原生投放任务

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/884a03d4-8017-46db-bc96-4e49881b2491.png) |
| 查询条件 | 日期段查询 | 左闭右闭，精确到日期 |
|  | 剧名 | 模糊搜索下拉单选 |
| 列表字段 | 任务id | 唯一即可 |
|  | 剧名(剧场) | 数据取自创建投放任务页面，展示参考上图即可 |
|  | 抖音号/账户 |
|  | 推广链 |
|  | 状态 | 枚举：执行中、完成、失败<br>*   执行中：创建投放任务后，系统会将任务中涉及的素材上传给巨量，这个过程状态=执行中<br>    <br>*   完成：视频素材全部上传完成=完成<br>    <br>*   失败：如果投放创建失败，需要在失败状态下展示失败原因，鼠标移入后，tip展示全部失败原因内容 |
|  | 执行时间 | 精确到秒 |
|  | 更新时间 |
|  | 创建时间 |
|  | 操作 | 【查看项目】<br>*   失败状态：查看项目按钮不可点击<br>    <br>*   成功状态：点击后跳转到全域项目页面（参考3.5.6页面说明） |
| 新建投放任务 | 模板信息 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/c01e54ff-6029-419e-8c53-f265fe99ba01.png)<br>*   选择模板：从全域模板管理页面选择配置好的模板名称（同时会将模板中已经配好的字段自动带到这个投放任务中）<br>    <br>*   查看详情：点击后，可以查看这个模板的明细字段，所有字段也都取自全域模板（参考下图）<br>    <br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/fdb31f8d-c20d-4fa2-9cee-72ee6df8ee12.png) |
|  | 资产信息 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/e7acbc1f-ee10-4038-a48a-f1f34d9f9f04.png)<br>*   短剧：模糊搜索下拉单选，选择短剧后自动带出资产信息里的其他字段<br>    <br>    *   短剧简称：短剧名称前2个字<br>        <br>    *   IAA推广链与IAP推广链：从三方剧场-端原生推广链库中获取数据源，这里跟随短剧自动带出<br>        <br>    *   推广链支持删除或新增/一行 |
|  | 选择账户 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/1b1fe1cd-15cd-4775-94b1-f11823d4b6c7.png)<br>*   抖音号：默认展示当前用户已分配的全部全域投放抖音号<br>    <br>*   账户：与抖音号一一对应，可从当前用户分配的账户中搜索选择<br>    <br>*   支持删除某一行，但至少保留1行 |
|  | 出价与预算 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/67f2c04f-27c9-4e5f-86a5-a9b7e75dd04c.png)<br>跟随全域投放模板自动带出，这里可手动修改，保存后以最终修改的数据为准 |
|  | 视频素材 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/dc344e74-dc6f-41ad-b757-3e3c41722a50.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/45cc73ca-9b54-4d9e-b4a8-428c6535791b.png)<br>1、系统会自动将该短剧目前已上传的，且归属于当前投手的素材全部带出<br>2、也可以点击【添加视频】按钮手动添加 |
|  | 标题选择 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/a66ca89b-8002-4978-bd79-d2c384ab87f3.png)![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/e68272a9-d116-4bbd-9342-3c17f65958dc.png)<br>*   手动选择标题<br>    <br>    *   选择标题：从自己的标题库中选择已有标题<br>        <br>    *   批量复制标题：批量新增标题，这里新增的标题是临时使用，不会插入到自己的标题库<br>        <br>*   自动选择标题：系统根据标题类型，自动给出一批标题<br>    <br>*   备注：自动选择标题库中，系统自动给出的这批标题，巨量没有接口，个人判断是代理商将自己的标题库开发给子商户使用（数据来源为代理商下面的所有子商户），开发看下是否可以爬一批弄下来使用<br>    <br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/af2483aa-7c03-4060-a743-26abf2213d8f.png) |
| 其他 | 保存投放任务 | 调用巨量创建项目接口：[https://open.oceanengine.com/labels/7/docs/1740868093375503](https://open.oceanengine.com/labels/7/docs/1740868093375503)<br>*   手动投放，与自动化投放在调接口时，传参字段delivery\_mode投放模式字段枚举定义：<br>    <br>    *   手动投放：MANUAL<br>        <br>    *   自动投放：PROCEDURAL |

###### 3.4.2、端原生自动化投放

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/3880eecb-0e13-435a-9884-3be4e63cc184.png) |
| 页面逻辑 |  | 1、这个页面不需要【新增】记录功能<br>2、页面所有的自动化任务都是系统自动创建（自动化创建策略来自于全域自动化投放策略-漫剧机器人） |
| 查询条件 | 规则类型 | 下拉单选![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/0bceebbd-00bf-4896-9177-91e037050ebb.png) |
|  | 短剧 | 模糊搜索（查的短剧列表字段） |
|  | 规则id | 精确查询 |
|  | 规则名称 | 模糊搜索 |
| 列表字段 | 规则id | 目前是6位数字，研发定义，唯一即可 |
|  | 规则名称 |  |
|  | 执行时间 |  |
|  | 模板名称 |  |
|  | 执行状态 |  |
|  | 短剧列表 | 根据自动投放规则，跑到的符合条件的短剧名称 |
|  | 创建时间 | 精确到秒 |
|  | 更新时间 |
| 操作 | 日志 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/9872b68d-1d9a-44a4-a54c-13a07d193c1d.png)<br>*   点击日志文字按钮，打开上图页面，页面展示的是这条自动化投放任务执行失败的日志记录 <br>    <br>*   如果制作人员当前没有针对短剧上传过素材，那么系统自动创建的投放任务就会执行失败 |

---

##### 3.5、巨量广告

:::
**巨量广告说明**

1、这个板块下没有配置内容，所有页面数据都是基于标准/全域广告投放创建后自动生成

2、标准/全域广告创建成功后，这里会分4个层级展示：账户→项目→广告→素材

评审时操作演示下关系

3、巨量广告版板块，其实就是分层级统计广告投放效果数据，我们的数据统计需要调巨量接口保存到本地数据库中，页面每次查询从库中读取数据

4、报表所有数据都从巨量接口获取，巨量有2个接口

接口1：查询所有维度、字段接口：[https://open.oceanengine.com/labels/7/docs/1755261744248832](https://open.oceanengine.com/labels/7/docs/1755261744248832)

附：接口1返回的指标和纬度结果[请至钉钉文档查看附件《自定义报表可用维度和指标》。](https://alidocs.dingtalk.com/document/preview?chInfo=im&cid=77665706803&dentryKey=qaN90XybuJGV4eEz&docKey=4maOgX308Jk0jlWN&dontjump=true&iframeQuery=anchorId%3DX02mumn98pdaqp8483qjnl&type=d&utm_medium=im_card&utm_source=im)

接口2：根据维度、字段值查询数据结果的接口：[https://open.oceanengine.com/labels/7/docs/1741387668314126](https://open.oceanengine.com/labels/7/docs/1741387668314126)
:::

###### 3.5.1、素材数据表

*   这个不是页面，是我们从巨量接口获取数据后，清洗到自己库中的一张数据表，巨量广告板块其他统计页面都从这张表中拿数据
    

| 字段 | 字段类型 | 字段说明说明 |
| --- | --- | --- |
| 时间 | 纬度 | MATERIAL\_DATA：stat\_time\_hour<br>*   巨量数据可以精细到小时纬度 |
| 素材名称 | 纬度 | MATERIAL\_DATA：ad\_platform\_material\_name |
| 素材id | 纬度 | MATERIAL\_DATA：material\_id |
| 广告 | 纬度 | MATERIAL\_DATA：cdp\_promotion\_name |
| 广告id | 纬度 | MATERIAL\_DATA：cdp\_promotion\_id |
| 项目 | 纬度 | MATERIAL\_DATA：cdp\_project\_name |
| 项目id | 纬度 | MATERIAL\_DATA：cdp\_project\_id |
| 账户 | 纬度 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/c70c2f4e-b85f-4e7e-9399-63ae425abde9.png)<br>我们系统中有广告id与账户id的绑定关系，广告id与账户是多对1的关系 |
| 账户id | 纬度 |
| 投放模式 | 纬度 | 投放模式：IAA、IAP<br>投放类型：全域、标准<br>根据广告id关联到我们自己的广告计划表中获取 |
| 投放类型 | 纬度 |
| 消耗 | 指标 | MATERIAL\_DATA：stat\_cost |
| 广告收益(当日) | 指标 | MATERIAL\_DATA：attribution\_billing\_game\_in\_app\_ltv\_1day |
| 广告总收益 | 指标 | MATERIAL\_DATA：stat\_pay\_amount |
| 回收金额 | 指标 | MATERIAL\_DATA：stat\_pay\_amount |
| 展示数 | 指标 | MATERIAL\_DATA：show\_cnt |
| 点击数 | 指标 | MATERIAL\_DATA：click\_cnt |
| 转化数 | 指标 | MATERIAL\_DATA：convert\_cnt |
| 激活数 | 指标 | MATERIAL\_DATA：active |

###### 3.5.2、账户

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/99121cd1-486e-4643-8f17-9eec28e43323.png) |
| 查询条件 | 类型 | 1、枚举：标准、全域<br>2、直接分2个tab去展示，2个tab下的报表字段相同 |
|  | 日期 | 1、左闭右闭<br>2、取值：对应素材数据表的日期字段 |
|  | 短剧投手 | 下拉单选，数据源是用户列表中打了投手标签的用户 |
|  | 账户 | 可按账户名或账户id进行搜索 |
|  | 投放模式 | 下拉单选：IAA、IAP |
| 列表字段 | 账户 | 从素材数据表获取 |
|  | 账户Id |
|  | 账户余额 | 1、页面打开后，列表会呈现当前用户所有投放账户，可通过[巨量批量查询余额接口](https://open.oceanengine.com/labels/7/docs/1799006604968971?origin=left_nav)，查询各账户余额数据<br>2、接口入参account\_type=AD<br>3、报表中的余额字段不受查询条件影响（查询条件可以控制这个账户展不展示，但是展示出来后，余额字段是实时从巨量获取的 ） |
|  | 消耗 | 从素材数据表获取 |
|  | 广告收益(当日) | 从素材数据表获取 |
|  | 广告总收益 | 从素材数据表获取 |
|  | 广告收益率(当日) | 从素材数据表获取并自己计算：广告收益(当日) / 消耗 |
|  | 广告总收益率 | 从素材数据表获取并自己计算：广告总收益 / 消耗 |
|  | 展示数 | 从素材数据表获取 |
|  | 平均千次展示费用 | 从素材数据表获取并自己计算：消耗 / 展示数 |
|  | 点击数 | 从素材数据表获取 |
|  | 点击率 | 从素材数据表获取并自己计算：点击数 / 展示数 |
|  | 平均点击单价 | 从素材数据表获取并自己计算：消耗 / 点击数 |
| 操作 | 【查看项目】 | 点击后跳转到项目页面 |
|  | 【查看广告】 | 点击后跳转到广告页面 |
| 其他 | 自定义列 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/7ca112ff-370c-4797-8a42-5f6f855a52ce.png)<br>1、支持页面列表自定义展示哪些字段<br>2、支持展示字段的自定义排序<br>3、列表数值类型字段，支持点击后，按数值大小正序/倒序排列 |

###### 3.5.3、项目

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/bbf0af87-a6e6-4224-9898-8338270027d5.png) |
| 逻辑说明 |  | 人工/系统创建广告成功后，如果广告投放配置中，一共用到了3个投放账户，每个账户配置5个广告，保存后生成的数据为：3个投放账户对应3个广告项目id，每个项目id对应5个广告id |
| 查询条件 | 日期范围 | 1、左闭右闭<br>2、取值：对应素材数据表的日期字段 |
|  | 投手 | 下拉单选，数据源是用户列表中打了投手标签的用户 |
|  | 短剧 | 下拉单选 |
|  | 项目名称 | 模糊查询 |
|  | 项目id | 精确查询 |
|  | 账户 | 可按账户名或账户id查询 |
|  | 投放模式 | 下拉单选：IAA、IAP |
| 列表字段 | 项目名称 |  |
|  | 项目id | 点击后会跳转到巨量系统的项目列表，示例如下<br>*   项目Id:[7690795487545131046](https://ad.oceanengine.com/promotion/promote-manage/project?aadvid=1877298281541892&filter_keyword=%25227690795487545131046%2522&filter_search_type=%25228%2522)<br>    <br>*   跳转链接：[https://ad.oceanengine.com/promotion/promote-manage/project?aadvid=1877298281541892&filter\_keyword=%25227690795487545131046%2522&filter\_search\_type=%25228%2522&uuid=a0c293a6-ab20-4f5f-94eb-9eaccda6e463](https://ad.oceanengine.com/promotion/promote-manage/project?aadvid=1877298281541892&filter_keyword=%25227690795487545131046%2522&filter_search_type=%25228%2522&uuid=a0c293a6-ab20-4f5f-94eb-9eaccda6e463) |
|  | 开关 | 可以在列表中，直接更改项目状态：暂停、开启 |
|  | 项目状态 | 暂停、开启 |
|  | 展示数 | 从素材数据表获取 |
|  | 平均千次展示费用 | 从素材数据表获取并自己计算：消耗 / 展示数 |
|  | 消耗 | 从素材数据表获取 |
|  | 点击数 | 从素材数据表获取 |
|  | 点击率 | 从素材数据表获取并自己计算：点击数 / 展示数 |
|  | 所属账户 | 从素材数据表获取 |
|  | 预算 | 从我们自己的项目表中获取（创建广告投放时，会分配项目预算）<br>*   如果项目预算是1万，广告投放创建成功后生成了2个项目id(因为分配了2个投放账户)，那么表中每个项目预算是5000<br>    <br>*   如果除不尽，四舍五入保留2位小数，且最后1个投放账户补全剩余金额（比如10除3，3个账户预算是3.33/3.33/3.34） |
|  | 广告收益(当日) | 从素材数据表获取 |
|  | 广告总收益 | 从素材数据表获取 |
|  | 广告收益率(当日) | 从素材数据表获取并自己计算：广告收益(当日) / 消耗 |
|  | 广告总收益率 | 从素材数据表获取并自己计算：广告总收益 / 消耗 |
|  | 转化数 | 从素材数据表获取 |
|  | 转化成本 | 从素材数据表获取并自己计算：消耗 / 转化数 |
|  | 转化率 | 从素材数据表获取并自己计算：转化数 / 点击数 |
|  | 激活数 | 从素材数据表获取 |
|  | 回收金额 | 从素材数据表获取 |
|  | 激活ARPU | 从素材数据表获取并自己计算：回收金额 / 激活数 |
|  | 激活成本 | 从素材数据表获取并自己计算：消耗 / 激活数 |
|  | 平均点击单价 | 从素材数据表获取并自己计算：消耗 / 点击数 |
|  | 推广链接id | 根据接口返回的广告id，从自己的广告投放表中获取 |
|  | 广告账户 id |
| 操作 | 【查看广告】 | 点击跳转到巨量广告-广告页面 |
|  | 【删除】 | 软删除 |
| 其他 | 批量开启 | 1、这3个是针对页面内的按钮功能做批量操作处理<br>2、项目开启/暂停/删除后，项目下所有广告也同时做对应状态变更 |
|  | 批量暂停 |
|  | 批量删除 |
|  | 批量修改预算 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/18329a6d-3bfd-444c-9b99-12e578140a5f.png)<br>1、这个修改的是广告配置中的目标预算（不是修改剩余预算金额）<br>2、如果批量勾选的广告项目，预算不一致，默认展示预算高的金额 |
|  | 支持自定义列 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/a5775305-1ecc-40a2-be62-8ab1a6871656.png)<br>1、支持页面列表自定义展示哪些字段<br>2、支持展示字段的自定义排序<br>3、列表数值类型字段，支持点击后，按数值大小正序/倒序排列 |

###### 3.5.4、广告

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/507c88db-9a08-4ea1-a553-d83eb6402fe3.png) |
| 逻辑说明 |  | 人工/系统创建广告成功后，如果广告投放配置中，一共用到了3个投放账户，每个账户配置5个广告，保存后生成的数据为：3个投放账户对应3个广告项目id，每个项目id对应5个广告id |
| 查询条件 | 日期范围 | 1、左闭右闭<br>2、取值：对应素材数据表的日期字段 |
|  | 投手 | 下拉单选，数据源是用户列表中打了投手标签的用户 |
|  | 广告名称 | 下拉单选 |
|  | 广告id | 精确查询 |
|  | 广告状态 | 1、下拉单选，默认查询全部<br>2、枚举如下<br>*   投放中：状态=开启的广告<br>    <br>*   已暂停：状态=开启的广告<br>    <br>*   已被项目暂停：需要关联广告所属项目，查看父级项目是否暂停 |
|  | 账户 | 可以查投放账户名，或账户id |
|  | 项目 | 可以查项目名，或项目Id |
|  | 推广外链 | 精确查询推广链 |
|  | 投放模式 | 下拉单选，IAA、IAP |
|  | 短剧名称 | 模糊查询 |
| 列表字段 | 广告名称 | 中台自己表中获取 |
|  | 广告id | 点击后会跳转到巨量系统的广告列表，示例如下<br>*   广告id：[7690795543181754378](https://ad.oceanengine.com/superior/promote-manage/ad?aadvid=1877298281541892&searchInput=%25227690795543181754378%2522)<br>    <br>*   跳转链接：[https://ad.oceanengine.com/promotion/promote-manage/ad?aadvid=1877298281541892&searchInput=%25227690795543181754378%2522](https://ad.oceanengine.com/promotion/promote-manage/ad?aadvid=1877298281541892&searchInput=%25227690795543181754378%2522) |
|  | 开关 | 列表中可以 直接更改状态 |
|  | 广告状态 | 对应查询条件中的广告状态 |
|  | 消耗 | 从素材数据表获取 |
|  | 广告收益 (当日) | 从素材数据表获取 |
|  | 广告总收益 | 从素材数据表获取 |
|  | 广告收益率(当日) | 从素材数据表获取并自己计算：广告收益(当日) / 消耗 |
|  | 广告总收益率 | 从素材数据表获取并自己计算：广告总收益 / 消耗 |
|  | 展示数 | 从素材数据表获取 |
|  | 平均千次展示费用 | 从素材数据表获取并自己计算：消耗 / 展示数 |
|  | 点击数 | 从素材数据表获取 |
|  | 点击率 | 从素材数据表获取并自己计算：点击数 / 展示数 |
|  | 平均点击单价 | 从素材数据表获取并自己计算：消耗 / 点击数 |
|  | 转化数 | 从素材数据表获取 |
|  | 转化率 | 从素材数据表获取并自己计算：转化数 / 点击数 |
|  | 广告预算 | 对应自己广告表中的广告预算 |
|  | 所属账户 | 父级投放账户名 |
|  | 转化成本 | 从素材数据表获取并自己计算：消耗 / 转化数 |
|  | 激活数 | 从素材数据表获取 |
|  | 激活成本 | 从素材数据表获取并自己计算：消耗 / 激活数 |
|  | 回收金额 | 从素材数据表获取 |
|  | 激活ARPU | 从素材数据表获取并自己计算：回收金额 / 激活数 |
|  | 项目名称 | 从我们自己表中获取 |
|  | 项目id |
|  | 广告id |
|  | 短剧名称 |
|  | 推广链接id |
|  | 短剧id |
| 其他 | 自定义列 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/12100ef2-09f2-4311-afc6-0d3bc9701ade.png)<br>1、支持页面列表自定义展示哪些字段<br>2、支持展示字段的自定义排序<br>3、列表数值类型字段，支持点击后，按数值大小正序/倒序排列 |
|  | 批量操作 | 支持批量开启、批量暂停、批量删除 |

###### 3.5.5、素材

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/0f0d8f88-e897-4dad-827a-f3f7698500a9.png) |
| 查询条件 | 日期 | 1、日期是单选<br>2、取值：对应素材数据表的日期字段 |
|  | 投手 | 下拉单选 |
|  | 广告账户 | 支持按广告账户或广告账户id查询 |
|  | 广告/计划id | 支持按广告 计划，或广告计划id查询 |
|  | 头条素材id | 对应素管理-视频表中的头条素材id |
| 列表字段 | 头条素材id |  |
|  | 素材 | 1、参考截图样式，默认展示素材第一帧截图，以及我们自己的视频id<br>2、素材可以在表格中直接预览播放 |
|  | 消耗 | 从素材数据表获取 |
|  | 转化数 | 从素材数据表获取 |
|  | 转化成本 | 从素材数据表获取并自己计算：消耗 / 转化数 |
|  | 展示数 | 从素材数据表获取 |
|  | 点击数 | 从素材数据表获取 |
|  | 点击率 | 从素材数据表获取并自己计算：点击数 / 展示数 |
|  | 平均点击单价 | 从素材数据表获取并自己计算：消耗 / 点击数 |
|  | 转化率 | 从素材数据表获取并自己计算：转化数 / 点击数 |
|  | 所属计划id | 对应我们自己投放表中的字段 |
|  | 所属计划 |
|  | 所属项目id |
|  | 所属项目 |
|  | 账户账户id |
|  | 所属账户 |
| 其他 | 自定义列 | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/12100ef2-09f2-4311-afc6-0d3bc9701ade.png)<br>1、支持页面列表自定义展示哪些字段<br>2、支持展示字段的自定义排序<br>3、列表数值类型字段，支持点击后，按数值大小正序/倒序排列 |

###### 3.5.6、全域项目

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/ffa5ae61-3638-4353-a8e5-4d4a2f8e7de5.png) |
| 页面说明 |  | 这个页面只展示全域投放的项目 |
| 查询条件 | 统计日期 | 1、左闭右闭<br>2、取值：对应素材数据表的日期字段 |
|  | 抖音号 | 下拉单选，根据我们自己表中，全域项目关联的抖音号进行查询 |
|  | 短剧 | 下拉单选 |
|  | 投手 | 下拉单选，对应用户表带投手标签的用户 |
|  | 主体 | 下拉搜索选择，根据我们自己表中，全域项目关联的主体进行查询 |
|  | 账户id | 根据我们自己表中，全域项目关联的对应id进行查询 |
|  | 项目id |
|  | 项目状态 | 下拉单选：开启、关闭 |
| 列表字段 | 项目 | 对应查询条件中的字段，列表展示样式参考图片<br>点击账户i后，可以跳转到巨量页面：[投放管理](https://ad.oceanengine.com/ad/web/manage?aadvid=1877202899030601&uuid=244df331-5a40-4bf8-b4ac-9a9410631078) |
|  | 剧名 |
|  | 主体 |
|  | 账户 |
|  | 抖音号 |
|  | 投手 |
|  | 项目状态 |
|  | 创建结果 | 1、全域项目创建的结果：创建成功、创建失败<br>2、失败原因有多种，可以参考下图<br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/e7187a7a-fcc4-4053-8b1e-9e143365f745.png) |
|  | 消耗 | 从素材数据表获取 |
|  | 预算 | 从投放创建表获取 |
|  | ROI系数 | 全域投放项目当前实时的ROI系数（因为算法会实时改系数） |
|  | 创建时间 | 项目创建时间 |
|  | 操作 | 【删除】：创建成功的项目支持点击删除，软删除 |

---

#### 4、数据报表

:::
**数据报表**

1、报表所有数据都从巨量接口获取，巨量有2个接口

接口1：查询所有维度、字段接口：[https://open.oceanengine.com/labels/7/docs/1755261744248832](https://open.oceanengine.com/labels/7/docs/1755261744248832)

附：接口1返回的指标和纬度结果[请至钉钉文档查看附件《自定义报表可用维度和指标》。](https://alidocs.dingtalk.com/document/preview?chInfo=im&cid=77665706803&dentryKey=qaN90XybuJGV4eEz&docKey=4maOgX308Jk0jlWN&dontjump=true&iframeQuery=anchorId%3DX02munk2x0qfqfz1ik03e&type=d&utm_medium=im_card&utm_source=im)

接口2：根据维度、字段值查询数据结果的接口：[https://open.oceanengine.com/labels/7/docs/1741387668314126](https://open.oceanengine.com/labels/7/docs/1741387668314126)

2、巨量接口用法

先调接口1，获取巨量能够提供哪些报表维度、字段

把挑选好的维度、指标放进请求体，然后再调接口2，拉取实际投放数据
:::

##### 4.1、利润报表

###### 4.1.1、利润统计概览

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/260d994e-8227-4288-82d0-082ed250de1b.png) |
| 页面说明 |  | 1、这个页面分5个tab统计(参考上面截图)，每个页面查询条件和列表字段相同<br>2、素材数据表数据可以到广告id纬度，与我们自己表中的广告id做映射，就可以拿到这个广告属于哪个剧场、剧类型，是IAA还是IAP，是全域还是标准投放等等 |
| 查询条件 | 日期 | 从素材数据表获取 |
|  | 分组筛选 | 投放组 |
|  | 剧场类型 | 默认就只有端原生一个选项（小程序目前不涉及） |
|  | 剧类型 | 默认就只有漫剧一个选项（真人剧目前不涉及） |
|  | 剧场 | 下拉单选：番茄漫剧，番茄番剧收费<br>*   对应就是广告投放创建时，选择的免费广告还是收费广告<br>    <br>*   免费=IAA，收费=IAP |
| 列表字段 | 日期 | 从素材数据表获取 |
|  | 消耗 |
|  | 回收 |
|  | 回收率 | 从素材数据表获取字段自己计算：回收 / 消耗 |
|  | 盈亏 | 从素材数据表获取字段自己计算：回收\*0.95 - 消耗\*roi<br>*   roi取值说明，参考表格下一行里的第5点 |
| 其他 |  | 1、赔付消耗字段目前不需要做<br>2、列表上方需要对消耗、回收、回收率、盈亏4个字段进行汇总<br>*   总盈亏字段：负数显示绿色，正数显示红色<br>    <br>*   **总回收率要用总回收/总消耗，不要用列表中每一行的回收率加起来除以行数**<br>    <br>3、点击列表中的日期，可以细分查看当天每个部门对应的字段数据<br>*   素材数据表有广告id纬度，广告id与投放账户id是多对1的关系，所以我们可以根据广告Id找到投放账户<br>    <br>*   投放账户与投手是多对1的关系，所以也可以关联到投手<br>    <br>*   最后根据投手所在部门进行分组统计表中的4个字段<br>    <br>4、列表4个字段，支持点击正序/倒序排列<br>5、在重置按钮边上增加一个按钮【ROI配置】，点击后打开弹窗页面，可以按日期段新增 roi系数（支持2位小数），弹窗页列表中展示的配置记录可编辑或删除<br>*   如果日期段有重复，取创建时间最新的1条记录执行<br>    <br>*   如果日期段没有覆盖到，则roi默认按1.00执行<br>    <br>*   利润报表板块共4个报表，每张报表都从利润统计概览页面取配置的roi值 |

###### 4.1.2、每日利润统计

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/f63b92ba-9a5d-4ec0-945a-33156dd71015.png) |
| 页面说明 |  | 这个页面与利润统计预览有2点差异<br>1、查询条件<br>*   利润统计预览：可以按投手所在组查询<br>    <br>*   每日利润统计：按投手查询<br>    <br>2、列表<br>*   利润统计预览：点击日期细分查看各投手所在组的各字段数据<br>    <br>*   每日利润统计：点击日期细分查看各平台对应的各字段数据<br>    <br>    *   备注：目前只有番茄平台，自己的鸥溪平台没有数据 |
| 查询条件 | 日期 | 从素材数据表获取 |
|  | 投手 | 打了投手标签的用户 |
|  | 剧类型 | 默认就只有漫剧一个选项（真人剧目前不涉及） |
|  | 平台 | 下拉单选：番茄，鸥溪<br>*   目前只有番茄有数据 |
| 列表字段 | 日期 | 从素材数据表获取 |
|  | 消耗 |
|  | 回收 |
|  | 回收率 | 从素材数据表获取字段自己计算：回收 / 消耗 |
|  | 盈亏 | 从素材数据表获取字段自己计算：回收\*0.95 - 消耗\*roi |
| 其他 |  | 1、赔付消耗字段目前不需要做<br>2、列表上方需要对消耗、回收、回收率、盈亏4个字段进行汇总<br>*   总盈亏字段：负数显示绿色，正数显示红色<br>    <br>*   **总回收率要用总回收/总消耗，不要用列表中每一行的回收率加起来除以行数**<br>    <br>3、点击列表中的日期，可以细分查看当天每个平台的投放数据<br>4、列表4个字段，支持点击正序/倒序排列 |

###### 4.1.3、投手利润统计

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/b9fce32c-1158-49a6-8983-fe679c20cc92.png) |
| 查询条件 | 日期 | 从素材数据表获取 |
|  | 剧类型 | 默认就只有漫剧一个选项（真人剧目前不涉及） |
|  | 平台 | 下拉单选：番茄，鸥溪<br>*   目前只有番茄有数据 |
| 列表字段 | 投手 | *   素材数据表有广告id纬度，广告id与投放账户id是多对1的关系，所以我们可以根据广告Id找到投放账户<br>    <br>*   投放账户与投手是多对1的关系，所以也可以关联到投手 |
|  | 消耗 | 从素材数据表获取 |
|  | 回收 | 从素材数据表获取 |
|  | 回收率 | 从素材数据表获取字段自己计算：回收 / 消耗 |
|  | 盈亏 | 从素材数据表获取字段自己计算：回收\*0.95 - 消耗\*roi |
| 其他 |  | 1、赔付消耗字段目前不需要做<br>2、列表上方需要对消耗、回收、回收率、盈亏4个字段进行汇总<br>*   总盈亏字段：负数显示绿色，正数显示红色<br>    <br>*   **总回收率要用总回收/总消耗，不要用列表中每一行的回收率加起来除以行数**<br>    <br>3、列表4个字段，支持点击正序/倒序排列 |

###### 4.1.4、组利润统计

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/cd3bc9b2-ba29-4525-932d-ce43498a87f2.png) |
| 查询条件 | 日期 | 从素材数据表获取 |
|  | 剧类型 | 默认就只有漫剧一个选项（真人剧目前不涉及） |
|  | 平台 | 下拉单选：番茄，鸥溪<br>*   目前只有番茄有数据 |
| 列表字段 | 部门 | *   素材数据表有广告id纬度，广告id与投放账户id是多对1的关系，所以我们可以根据广告Id找到投放账户<br>    <br>*   投放账户与投手是多对1的关系，所以也可以关联到投手<br>    <br>*   最后根据投手所在部门进行分组统计表中的4个字段 |
|  | 消耗 | 从素材数据表获取 |
|  | 回收 | 从素材数据表获取 |
|  | 回收率 | 从素材数据表获取字段自己计算：回收 / 消耗 |
|  | 盈亏 | 从素材数据表获取字段自己计算：回收\*0.95\` - 消耗\*roi |
| 其他 |  | 1、赔付消耗字段目前不需要做<br>2、列表上方需要对消耗、回收、回收率、盈亏4个字段进行汇总<br>*   总盈亏字段：负数显示绿色，正数显示红色<br>    <br>*   **总回收率要用总回收/总消耗，不要用列表中每一行的回收率加起来除以行数**<br>    <br>3、列表4个字段，支持点击正序/倒序排列<br>4、点击列表中的部门，可以细分查看部门下每个投手的数据 |

##### 4.2、素材报表

###### 4.2.1、素材消耗

| 类型 | 字段 | 字段说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/708197e2-2427-4d1c-b6fb-4c9b77fb1717.png) |
| 查询条件 | 日期 | 左闭右闭，对应素材数据表日期字段 |
|  | 投手 | 下拉单选，对应带有投手标签的用户 |
|  | 上传者 | 对应素材管理-视频页面，视频素材的上传人 |
| 列表字段 | 日期 | 从素材数据表获取 |
|  | 素材名称 | 按截图中的样式展示：视频第一帧作为封面+素材名称+素材iD |
|  | 剧名 | 从我们自己的视频素材页面获取 |
|  | 消耗 | 从素材数据表获取 |
|  | 素材类型 | 从我们自己的视频素材页面获取 |
|  | 归属 | 从我们自己的视频素材页面获取 |
|  | 上传者 | 从我们自己的视频素材页面获取 |
|  | 投手 | 从我们自己的视频素材页面获取 |
|  | 操作 | 【数据详情】点击后打开下表页面 |
| 其他 |  | *   列表右上方需要对消耗值求和<br>    <br>*   支持自定义列，及字段展示顺序调整<br>    <br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/c0d004e3-0e86-42bc-8f98-f7adf3c9a254.png) |

*   【数据详情】页面
    

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/d28ba397-bc48-4e69-bb31-7414ffce332a.png) |
| 查询条件 | 投放类型 | 下拉单选：标准广告、全域广告、全部<br>*   默认展示全部 |
| 列表字段 | 广告id/广告名称/项目id/头条素材id/投手 | 1、5个字段合并到1个字段展示（这里要统一下字段名叫法）<br>*   创意=广告id<br>    <br>*   广告主=广告名称<br>    <br>*   计划=项目<br>    <br>*   计划id=项目id<br>    <br>*   素材id：76开头的是头条素材id，12开头的是中台素材id<br>    <br>    *   这里展示的是头条素材id<br>        <br>2、展示样式参考截图 <br>3、广告创建中，会关联引用素材，这里根据关联关系找到素材的上级广告、项目<br>4、项目与投放账户是多对1的关系，投放账  户与投手是多对1的关系，所以根据这个关系可以找到投手 |
|  | 消耗 | 从素材数据表获取 |
|  | 展示数 | 从素材数据表获取 |
|  | 点击数 | 从素材数据表获取 |
|  | 点击率 | 从素材数据表获取并自己计算：点击数 / 展示数 |
|  | 平均点击单价 | 从素材数据表获取并自己计算：消耗 / 点击数 |
|  | 平均千次展示费用 | 从素材数据表获取并自己计算：消耗 / 展示数 |
|  | 转化数 | 从素材数据表获取 |
|  | 转化率 | 从素材数据表获取并自己计算：转化数 / 点击数 |
|  | 平均转化成本 | 素材数据表获取并自己计算：消耗 / 转化数 |

###### 4.2.2、剪辑师消耗

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/d800cb9c-6cd2-4612-b41b-daa8ba9f7621.png) |
| 查询条件 | 日期 | 对应素材数据表日期字段 |
|  | 素材手 | 1、下拉搜索单选<br>2、对应素材的上传人 |
|  | 素材手分组 | 素材上传人所在的部门 |
| 字段 | 日期 | 从素材数据表获取 |
|  | 素材手 | 我们自己表中的素材上传人 |
|  | 总消耗(不包含nobid) | *   消耗=素材数据表中的消耗字段（这里的总消耗是标准+全域的消耗）<br>    <br>*   nobid判断：广告投放中，如果模板名称包含NB与cbo，就是nobid素材，所以这里需要带着素材数据表中的项目id到我们自己表中查使用的模板名称，判断是否是nobid素材 |
|  | 标准非nobid消耗 | 上述总消耗中，找出标准投放的非nobid消耗<br>*   同样是带着素材数据表中的项目id关联我们自己项目表，找到标准投放 |
|  | 标准nobid消耗 | 上述总消耗中，找出标准投放的nobid消耗<br>*   同样是带着素材数据表中的项目id关联我们自己项目表，找到标准投放 |
|  | 全域gmv | *   gmv=素材数据表中的回收金额<br>    <br>*   24小时这个文字可以忽略，查询条件时间跨度选多久就是多久<br>    <br>*   全域：根据素材数据表中的项目id关联自己的投放表，判断是否是全域投放 |
|  | 所在组平均roi | 数据从素材数据表获取字段自己计算<br>*   roi公式=回收金额/消耗<br>    <br>*   这里要先取登录用户所在部门下的所有素材手，然后看这些素材手上传的素材得到平均roi |
|  | 总消耗 | 取素材数据表里的消耗字段 |
| 其他 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/39e75e81-e152-429d-8e9d-523767ae417d.png)<br>*   支持自定义列，及字段展示顺序调整 |

###### 4.2.3、素材报表

*   **短剧统计tab**
    

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/267f4b99-0180-4d3e-bee7-f78d25e8c035.png) |
| 查询条件 | 日期 | *   对应素材数据表的日期<br>    <br>*   左闭右闭 |
|  | 短剧名称 | 模糊搜索 |
|  | 新老剧 | *   截图页面中的流转剧查询不用做，改为新老剧查询<br>    <br>*   下拉单选：新剧、老剧、默认查询全部<br>    <br>    *   新剧：预估上线时间为当天的短剧<br>        <br>    *   老剧：遇上上线时间为昨天及之前的短剧 |
| 列表字段 | 短剧名称 |  |
|  | 素材数 | 素材管理-视频页面，这个短剧对应的素材数 |
|  | ~~非转码素材数~~ | ~~本次不用做~~ |
|  | 消耗 | 从素材数据表获取 |
| 其他 |  | *   列表左上方需要做素材数，以及消耗做合计<br>    <br>*   列表中的短剧名称可点击，点击后跳转到素材统计tab页<br>    <br>    *   素材统计tab页-短剧名称查询条件，要默认把点击的短剧名称带上查询 |

*   **短剧素材手统计tab**
    

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/1e04c15c-2f1d-4896-a2ba-6e66e6d3d438.png) |
| 查询条件 | 日期 | *   对应素材数据表的日期<br>    <br>*   左闭右闭 |
|  | 短剧名称 | 模糊搜索 |
|  | 素材手 | 下拉单选，支持模糊搜索 |
|  | 新老剧 | *   截图页面中的流转剧查询不用做，改为新老剧查询<br>    <br>*   下拉单选：新剧、老剧、默认查询全部<br>    <br>    *   新剧：预估上线时间为当天的短剧<br>        <br>    *   老剧：预估上线时间为昨天及之前的短剧 |
| 列表字段 | 短剧名称 |  |
|  | 素材手 | *   管理员在这个页面可查看所有素材手的数据，如果当前是素材手账号，那么只能看到自己的数据 |
|  | 素材数 | 素材管理-视频页面，这个短剧对应的素材数 |
|  | ~~非转码素材数~~ | ~~本次不用做~~ |
|  | 消耗 | 从素材数据表获取 |
| 其他 |  | *   列表左上方需要做素材数，以及消耗做合计<br>    <br>*   列表中的短剧名称可点击，点击后跳转到素材统计tab页<br>    <br>    *   素材统计tab页-短剧名称查询条件，要默认把点击的短剧名称、素材手带上查询 |

*   **素材统计tab**
    

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/804ac20d-3897-4aa9-a698-4e25b2136212.png) |
| 查询条件 | 日期 | *   对应素材数据表的日期<br>    <br>*   左闭右闭 |
|  | 短剧名称 | 模糊搜索 |
|  | 素材手 | 下拉单选，支持模糊搜索 |
|  | 新老剧 | *   截图页面中的流转剧查询不用做，改为新老剧查询<br>    <br>*   下拉单选：新剧、老剧、默认查询全部<br>    <br>    *   新剧：预估上线时间为当天的短剧<br>        <br>    *   老剧：遇上上线时间为昨天及之前的短剧 |
| 列表字段 | 视频 | *   取素材视频第一帧作为封面<br>    <br>    *   注意：这个是素材视频，不是短剧视频<br>        <br>*   列表中，输入移入封面上，可预览视频<br>    <br>![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/1a7a3a7c-cfd3-4cf4-9b58-e2c49319bad4.png) |
|  | 短剧名称 |  |
|  | 素材手 | *   管理员在这个页面可查看所有素材手的数据，如果当前是素材手账号，那么只能看到自己的数据 |
|  | 素材名称 | 素材管理-视频页面，这个素材视频对应的素材名称 |
|  | ~~非转码素材数~~ | ~~本次不用做~~ |
|  | 消耗 | 从素材数据表获取 |
| 其他 |  | *   列表左上方需要做素材数，以及消耗做合计 |

*   **未上NB新剧tab**
    

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/38b079f8-6ec5-4960-acba-a4e09019a753.png) |
| 查询条件 | 日期 | *   对应漫剧流转剧库中的预估投放时间<br>    <br>*   左闭右闭 |
|  | 短剧名称 | 模糊搜索 |
| 列表字段 | 短剧名称 | 预估投放时间是所选日期当天的短剧 |
|  | 素材数 | 1、关联已创建的投放计划，看使用了模板名称包含NB或者CBO的就是NB投放<br>2、然后NB投放里对应的短剧就是NB剧<br>*   如果一部剧同时被NB和非NB投放计划引用，那么依旧算NB剧<br>    <br>3、然后看这个NB计划里，这部剧使用的素材数（注意，不是这部剧在视频库里的所有素材） |

###### 4.2.4、剪辑师统计

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| 页面截图 |  | ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgX308Jk0jlWN/img/a6a70df7-7508-4eb6-a115-a12d8d179c56.png) |
| 查询条件 | 日期 | *   对应漫剧流转剧库中的预估投放时间<br>    <br>*   左闭右闭 |
|  | 素材手 | *   下拉单选，支持搜索<br>    <br>    *   一般只有管理权限才需要搜索，素材手账号只能搜自己<br>        <br>*   素材手分组：下拉单选，与素材手是级联关系 |
|  | ~~流转剧~~ | ~~不做~~ |
| 列表字段 | 日期 | 年月日格式 |
|  | 素材手 | 只有自己（管理员可以查看所有） |
|  | 今日新剧数 | select 素材手上传的视频素材对应的短剧<br>where 预估发布时间=所选时间<br>and  所选时间有消耗数据的 |
|  | 今日剧目数 | select 素材手上传的视频素材对应的短剧<br>where   所选时间有消耗数据的 |
|  | 今日素材数 | select 素材手上传的视频素材<br>where   所选时间有消耗数据的 |
|  | 总消耗 | 取素材数据表的消耗数据 |
|  | 操作 | 【数据详情】：点击后跳转素材报表-短剧素材手统计tab，需要将素材手名称默认带入查询条件 |
| 其他 |  | 1、今日新剧数、日剧目数、今日素材数、总消耗4个字段支持点击排序<br>2、上述这4个字段需要有汇总行（参考截图） |