## 叙事路线设计

(自动化设计版本，未必来得及实现)

#### Task 1: Profile Sailor Shift’s Career & Network (Sailor Shift 的职业与网络画像)

核心 Panel 联动：`Career Arc` + `Influence Galaxy`

- 第一幕：巨星的崛起 (Career Arc)：
  - 操作：全局聚焦在 Sailor Shift。时间轴高亮她的首发作品到爆发期的节点。
  - 叙事：展示她发片频率的节奏，以及她是如何/何时获得大量 Notable 标签的，定调她的职业弧线。
- 第二幕：溯源与音乐根基 (Influence Galaxy)：
  - 操作：以 Sailor Shift 为中心节点展开子图，过滤出 `InStyleOf` 关系。
  - 叙事：视觉上直接解答“谁影响了她”，展示她的音乐灵感来源。
- 第三幕：Ivy Echoes 的羁绊与散叶 (Influence Galaxy)：
  - 操作：在网络中高亮（或添加子图扩展）她的前乐队 "Ivy Echoes" 及其成员。筛选出 `PerformerOf` 和 `MemberOf`。
  - 叙事：讲述“聚是一团火，散是满天星”的故事。通过连线观察这些前队友是如何直接影响她的（是否有后期的共同创作），以及前队友们各自辐射出的间接影响力（他们又影响了谁），展示这个小圈子对整个生态的冲击。

#### Task 2: Map the Spread of Oceanus Folk (映射 Oceanus Folk 的传播)

核心 Panel 联动：`Genre Flow` + `Career Arc` + `Influence Galaxy`

- 第一幕：爆炸还是渐进？ (Genre Flow / Career Arc)：
  - 操作：全局流派筛选锁定 `Oceanus Folk`。观察 `Genre Flow` 中的面积厚度或 `Career Arc` 全局按年聚合的发片量。
  - 叙事：如果在图表上看到一个短期内陡直上升的峰值（Spike），就可以定性为“Explosive（爆发式）”；如果是多年的平缓增厚，则是“Gradual（渐进式）”。
- 第二幕：跨流派的演变轨迹 (Genre Flow)：
  - 操作：将 `Indie Pop` 也加入高亮白名单。在桑基图或河流图中观察两者的流动。
  - 叙事：观察在特定的时间节点，`Oceanus Folk` 的流量是否分化、交融进了 `Indie Pop`。
- 第三幕：寻找破圈推手 (Influence Galaxy)：
  - 操作：结合网络图，找出同时拥有（或连接了）这两个流派标签的核心桥梁节点（Bridge Nodes）。
  - 叙事：将宏观的流派演变落实到具体的几位关键艺术家或几次现象级合作上，故事更加具体。

#### Task 3: Define & Predict the "Rising Star" (定义并预测“明日之星”)

核心 Panel 联动：`Star Profiler` + `Career Arc`

- 第一幕：定义“巨星模型” (Star Profiler)：
  - 操作：在雷达图/属性矩阵中引入已建立的巨星（Established Artists，如 Sailor Shift）。
  - 叙事：提取她们在成名前的共性特征（例如：高频发作、跨流派连接度高、网络中心度高、Fame Gap 潜伏期长短等），以此定义何为“Rising Star”。
- 第二幕：大浪淘沙 (Star Profiler -> Career Arc)：
  - 操作：运用“巨星模型”的特征权重，对目前活动在近几年的 `Oceanus Folk` 新人进行匹配和排序。将得分最高的几个候选人放入 `Career Arc` 进行对比。
  - 叙事：展示这些候选人的轨迹，验证他们是否正好处于类似大牌当年爆发前的“上升前夜”。
- 第三幕：预测与公布 (全景)：
  - 操作：揭晓预测的 3 位新星，并展示他们在 `Influence Galaxy` 中日益密集的合作网络。
  - 叙事：用数据支撑预测，说明为什么这三位拥有接棒下一个时代的能力。



## 初版视频脚本

### Task 1 追踪 Sailor Shift 的星路与关系网

(Voiceover/旁白)： “我们的第一个任务是给当红歌手 Sailor Shift 绘制职业画像，并溯源她的关系网络。”



(Action/画面 1.1)：

1. 在全局搜索框输入 `Sailor Shift` 并选中。
2. 鼠标滑向 A. Career Arc (职业时轴)。
3. 框选她从出道到爆发的那几年时间。

(Voiceover/旁白)： “首先看她的 Career Arc（职业时轴）。通过全局过滤，我们清晰地看到了她作品的发布频率。注意看这里的颜色高亮（指向 notable 标识），在经过一段相对平静的酝酿期后，她的 Notable（知名）作品在某一年迎来了集中爆发，确立了她的巨星地位。”



(Action/画面 1.2)：

1. 视线转移到 B. Influence Galaxy (影响力网络)。
2. 在关系过滤器中勾选 `InStyleOf` 和 `MemberOf`。
3. 点击展开 Sailor Shift 的上游节点。

(Voiceover/旁白)： “那么，是谁影响了她？我们把目光转向 Influence Galaxy（影响力网络）。以她为中心展开风格溯源（In Style Of 连线），我们可以看到她深厚的音乐根基。 更重要的是，当我们高亮她曾经所在的乐队 Ivy Echoes 时（点击/悬停前乐队成员），故事变得非常有趣。聚是一团火，散是满天星。她的前队友们不仅直接参与了她早期的核心创作，而且各自开枝散叶，在这个子网络中形成了巨大的间接影响力辐射圈。”



### Task 2 映射 Oceanus Folk 的流派蔓延

(Voiceover/旁白)： “接下来，我们将视角从个人放大到整个生态，看看 Oceanus Folk 这个流派是如何传播开来的。”



(Action/画面 2.1)：

1. 取消 Sailor Shift 的个人选中状态。
2. 在全局流派筛选中，只勾选 `Oceanus Folk` 和 `Indie Pop`。
3. 视线转向 C. Genre Flow (流派演变图/河流图)。

(Voiceover/旁白)： “在 Genre Flow（流派演变图） 中，蓝色的色块代表 Oceanus Folk。我们可以直观地看到，它的增长并不是平缓的，而是在特定年份出现了一个陡峭的爬升（用鼠标指向增宽的区域）—— 这是一次典型的**爆炸式（Explosive）**增长。”



(Action/画面 2.2)：

1. 鼠标在河流图中，框选 Oceanus Folk 与 Indie Pop 发生交汇/融合的年份区间。
2. 此时左侧的 Influence Galaxy 自动更新，显示这几年内的核心人物。
3. 鼠标悬停在同时连接这两个流派的几个“桥梁节点（Bridge Nodes）”上。

(Voiceover/旁白)： “随着时间推移，Oceanus Folk 开始与 Indie Pop 发生交汇。得益于系统强大的跨视图联动（Brushing & Linking），当我们框选这段融合期时，影响力网络立刻帮我们找出了背后的推手。正是这几位处于结构洞位置的跨界艺术家（指向桥梁节点），促成了 Oceanus Folk 向 Indie Pop 的成功破圈演变。”



### Task 3 定义并预测“明日之星”

(Voiceover/旁白)： “了解了天后的轨迹和流派的趋势后，最激动人心的任务来了：我们能否用数据预测出下一代的 Rising Star（明日之星）？”



(Action/画面 3.1)：

1. 将目光移向 D. Star Profiler (艺人画像/雷达图)。
2. 选中几位已经功成名就的艺术家（包括 Sailor Shift），展示他们的雷达图叠加。

(Voiceover/旁白)： “在 Star Profiler（艺人画像） 中，我们提取了成功巨星的共性特征。通过雷达图对比，我们发现一个‘准巨星’通常具备：早期的稳定高产（高发作频率）、广泛的跨界合作（高网络中心度），以及对前沿流派极强的吸附能力。”



(Action/画面 3.2)：

1. 在数据面板/搜索栏切换到我们筛选出的 3 位“候选新人”。
2. 雷达图切换为新人的画像，显示他们的图形分布与巨星当年的历史数据高度吻合。
3. 鼠标最后滑回 A. Career Arc，将这三位新人的当前轨迹与 Sailor Shift 的早期轨迹放在同一时间轴上对比。

(Voiceover/旁白)： “我们将这个‘巨星模型’套用到近年活跃的新人中，锁定了这三位候选人。 大家看这三位新人的特征雷达图，简直就是年轻版 Sailor Shift 的翻版。最后，让我们在 Career Arc 中并排对比。这三位新人目前的上升斜率、甚至是成名作前的‘潜伏期（Fame Gap）’，都暗示着他们正处于爆发的前夜。 综合网络结构和时序轨迹，我们有理由相信，这三位就是接管下一代 Oceanus 音乐市场的 Rising Stars。”