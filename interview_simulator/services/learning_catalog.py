"""Generate the scalable Interview Learning catalog independently from the UI."""

from interview_simulator.utils.common import safe_json_dumps, safe_json_loads


COMPANIES = [
    "Alphabet (Google)", "Microsoft", "Amazon", "Apple", "NVIDIA", "Meta", "Netflix",
    "Adobe", "Salesforce", "Oracle", "IBM", "Intel", "AMD", "Tesla", "Uber", "Airbnb",
    "LinkedIn", "PayPal", "Walmart", "Flipkart", "PhonePe", "Razorpay", "Swiggy", "Zomato",
    "Atlassian", "Cisco", "Qualcomm", "Samsung", "Dell", "HP", "Accenture", "Deloitte",
    "JPMorgan Chase", "Goldman Sachs", "Morgan Stanley", "TCS", "Infosys", "Wipro",
    "Cognizant", "Capgemini",
]

FREQUENCIES = ["Very Common", "Common", "Moderate", "Rare"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]


CODING_PROBLEMS = [
    ("Two Sum", "Arrays", "Use a hash map from value to index while scanning once.", "O(n)", "O(n)", "nums=[2,7,11,15], target=9 -> [0,1]", """def two_sum(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        needed = target - value
        if needed in seen:
            return [seen[needed], index]
        seen[value] = index
    return []"""),
    ("Longest Substring Without Repeating Characters", "Sliding Window", "Move a left boundary past the last position of each repeated character.", "O(n)", "O(k)", "'abcabcbb' -> 3", """def longest_unique(text):
    last, left, best = {}, 0, 0
    for right, char in enumerate(text):
        left = max(left, last.get(char, -1) + 1)
        last[char] = right
        best = max(best, right - left + 1)
    return best"""),
    ("Merge Intervals", "Sorting", "Sort by start time, then merge when the next interval overlaps the current end.", "O(n log n)", "O(n)", "[[1,3],[2,6],[8,10]] -> [[1,6],[8,10]]", """def merge(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result"""),
    ("Valid Parentheses", "Stacks", "Push opening brackets and require each closing bracket to match the stack top.", "O(n)", "O(n)", "'{[()]}' -> true", """def valid_parentheses(text):
    pairs, stack = {')': '(', ']': '[', '}': '{'}, []
    for char in text:
        if char in pairs.values(): stack.append(char)
        elif char in pairs and (not stack or stack.pop() != pairs[char]): return False
    return not stack"""),
    ("Reverse a Linked List", "Linked Lists", "Iteratively redirect each next pointer while preserving the unvisited suffix.", "O(n)", "O(1)", "1->2->3 -> 3->2->1", """def reverse(head):
    previous = None
    while head:
        following = head.next
        head.next = previous
        previous, head = head, following
    return previous"""),
    ("Detect a Linked List Cycle", "Linked Lists", "Advance slow by one and fast by two; a meeting proves a cycle.", "O(n)", "O(1)", "1->2->3->2 -> true", """def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow is fast: return True
    return False"""),
    ("Binary Search", "Binary Search", "Maintain an inclusive sorted search range and discard half after every comparison.", "O(log n)", "O(1)", "[1,3,5,7], target=5 -> 2", """def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if nums[mid] == target: return mid
        if nums[mid] < target: left = mid + 1
        else: right = mid - 1
    return -1"""),
    ("Search a Rotated Sorted Array", "Binary Search", "At least one half is sorted; test whether the target lies inside it before discarding a half.", "O(log n)", "O(1)", "[4,5,6,7,0,1,2], target=0 -> 4", """def search_rotated(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target: return mid
        if nums[left] <= nums[mid]:
            if nums[left] <= target < nums[mid]: right = mid - 1
            else: left = mid + 1
        else:
            if nums[mid] < target <= nums[right]: left = mid + 1
            else: right = mid - 1
    return -1"""),
    ("Maximum Subarray", "Dynamic Programming", "Kadane's algorithm keeps the best subarray ending here and the best seen globally.", "O(n)", "O(1)", "[-2,1,-3,4,-1,2,1] -> 6", """def max_subarray(nums):
    ending = best = nums[0]
    for value in nums[1:]:
        ending = max(value, ending + value)
        best = max(best, ending)
    return best"""),
    ("Climbing Stairs", "Dynamic Programming", "The number of ways to reach a step is the sum of the previous two states.", "O(n)", "O(1)", "n=5 -> 8", """def climb_stairs(n):
    previous, current = 1, 1
    for _ in range(n): previous, current = current, previous + current
    return previous"""),
    ("Coin Change", "Dynamic Programming", "Build the minimum coins for every amount using previously solved smaller amounts.", "O(amount * coins)", "O(amount)", "coins=[1,2,5], amount=11 -> 3", """def coin_change(coins, amount):
    dp = [0] + [amount + 1] * amount
    for value in range(1, amount + 1):
        for coin in coins:
            if coin <= value: dp[value] = min(dp[value], dp[value-coin] + 1)
    return dp[amount] if dp[amount] <= amount else -1"""),
    ("Longest Increasing Subsequence", "Dynamic Programming", "Maintain the smallest possible tail for an increasing subsequence of each length.", "O(n log n)", "O(n)", "[10,9,2,5,3,7,101,18] -> 4", """def lis_length(nums):
    from bisect import bisect_left
    tails = []
    for value in nums:
        index = bisect_left(tails, value)
        if index == len(tails): tails.append(value)
        else: tails[index] = value
    return len(tails)"""),
    ("Number of Islands", "Graphs", "Start a flood fill from each unvisited land cell and mark its entire component.", "O(rows * cols)", "O(rows * cols)", "two disconnected land groups -> 2", """def num_islands(grid):
    def visit(r, c):
        if r < 0 or c < 0 or r == len(grid) or c == len(grid[0]) or grid[r][c] != '1': return
        grid[r][c] = '0'
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)): visit(r+dr, c+dc)
    count = 0
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == '1': count += 1; visit(r, c)
    return count"""),
    ("Shortest Path in an Unweighted Graph", "Graph Algorithms", "Breadth-first search visits vertices in nondecreasing distance from the source.", "O(V + E)", "O(V)", "A-B-C and A-D-C -> distance A to C is 2", """def shortest_path(graph, source, target):
    from collections import deque
    queue, parent = deque([source]), {source: None}
    while queue:
        node = queue.popleft()
        if node == target: break
        for neighbor in graph[node]:
            if neighbor not in parent: parent[neighbor] = node; queue.append(neighbor)
    if target not in parent: return []
    path = []
    while target is not None: path.append(target); target = parent[target]
    return path[::-1]"""),
    ("Topological Sort", "Graphs", "Kahn's algorithm repeatedly removes zero-indegree vertices and updates their neighbours.", "O(V + E)", "O(V)", "prerequisite DAG -> valid course order", """def topological_sort(graph, indegree):
    from collections import deque
    queue = deque(node for node in graph if indegree[node] == 0)
    order = []
    while queue:
        node = queue.popleft(); order.append(node)
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0: queue.append(neighbor)
    return order if len(order) == len(graph) else []"""),
    ("Binary Tree Level Order Traversal", "Binary Trees", "Use a queue and process exactly the current queue length for each level.", "O(n)", "O(n)", "[3,9,20,null,null,15,7] -> [[3],[9,20],[15,7]]", """def level_order(root):
    from collections import deque
    if not root: return []
    queue, levels = deque([root]), []
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft(); level.append(node.val)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        levels.append(level)
    return levels"""),
    ("Validate a Binary Search Tree", "Binary Search Trees", "Carry strict lower and upper bounds down the tree rather than comparing only with a parent.", "O(n)", "O(h)", "[2,1,3] -> true", """def valid_bst(root):
    def check(node, low, high):
        if not node: return True
        if not low < node.val < high: return False
        return check(node.left, low, node.val) and check(node.right, node.val, high)
    return check(root, float('-inf'), float('inf'))"""),
    ("Kth Largest Element", "Heaps", "Keep a min-heap of size k so its root is the kth largest value seen.", "O(n log k)", "O(k)", "[3,2,1,5,6,4], k=2 -> 5", """def kth_largest(nums, k):
    import heapq
    heap = []
    for value in nums:
        heapq.heappush(heap, value)
        if len(heap) > k: heapq.heappop(heap)
    return heap[0]"""),
    ("Implement an LRU Cache", "Hash Maps", "Combine a hash map with a doubly linked list ordered by recency.", "O(1) per operation", "O(capacity)", "put(1,1), get(1) -> 1", """from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity): self.capacity, self.data = capacity, OrderedDict()
    def get(self, key):
        if key not in self.data: return -1
        self.data.move_to_end(key); return self.data[key]
    def put(self, key, value):
        self.data[key] = value; self.data.move_to_end(key)
        if len(self.data) > self.capacity: self.data.popitem(last=False)"""),
    ("Trie Prefix Search", "Tries", "Store one character per edge and mark terminal nodes for complete words.", "O(length)", "O(total characters)", "insert 'cat'; startsWith 'ca' -> true", """class Trie:
    def __init__(self): self.root = {}
    def insert(self, word):
        node = self.root
        for char in word: node = node.setdefault(char, {})
        node['#'] = True
    def starts_with(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node: return False
            node = node[char]
        return True"""),
    ("Generate Permutations", "Backtracking", "Choose an unused value, recurse, then undo the choice to explore another branch.", "O(n * n!)", "O(n)", "[1,2,3] -> 6 permutations", """def permutations(nums):
    result = []
    def search(path, remaining):
        if not remaining: result.append(path[:]); return
        for index, value in enumerate(remaining):
            search(path + [value], remaining[:index] + remaining[index+1:])
    search([], nums)
    return result"""),
    ("Minimum Window Substring", "Sliding Window", "Expand until all required counts are met, then shrink while the window remains valid.", "O(n + m)", "O(k)", "s='ADOBECODEBANC', t='ABC' -> 'BANC'", """def min_window(s, t):
    from collections import Counter
    need, missing, left, best = Counter(t), len(t), 0, (0, float('inf'))
    for right, char in enumerate(s, 1):
        if need[char] > 0: missing -= 1
        need[char] -= 1
        while missing == 0:
            if right-left < best[1]-best[0]: best = (left, right)
            need[s[left]] += 1
            if need[s[left]] > 0: missing += 1
            left += 1
    return '' if best[1] == float('inf') else s[best[0]:best[1]]"""),
    ("Product of Array Except Self", "Prefix Sum", "Multiply prefix products in a forward pass and suffix products in a backward pass.", "O(n)", "O(1) extra", "[1,2,3,4] -> [24,12,8,6]", """def product_except_self(nums):
    result, prefix = [1] * len(nums), 1
    for index, value in enumerate(nums): result[index], prefix = prefix, prefix * value
    suffix = 1
    for index in range(len(nums)-1, -1, -1): result[index], suffix = result[index] * suffix, suffix * nums[index]
    return result"""),
    ("SQL Top Customers", "SQL", "Aggregate orders by customer, filter if needed, then sort the aggregate rather than individual rows.", "O(rows log groups)", "O(groups)", "orders -> top five customers by revenue", """SELECT customer_id, SUM(amount) AS revenue
FROM orders
GROUP BY customer_id
ORDER BY revenue DESC
LIMIT 5;"""),
    ("Producer Consumer Queue", "Multithreading", "Use a bounded synchronized queue so producers block when full and consumers block when empty.", "O(1) queue operation", "O(capacity)", "two producers and consumers share a bounded buffer", """from queue import Queue
from threading import Thread
buffer = Queue(maxsize=10)
def produce(items):
    for item in items: buffer.put(item)
def consume(count):
    for _ in range(count): process(buffer.get()); buffer.task_done()"""),
]


TECHNICAL_CONCEPTS = [
    ("Array vs Linked List", "Data Structures", "Arrays provide cache-friendly O(1) indexing; linked lists provide pointer-based insertion but poor locality."),
    ("Stack vs Queue", "Data Structures", "A stack is LIFO and suits nesting or undo; a queue is FIFO and suits scheduling or breadth-first work."),
    ("Hash Collision Resolution", "Hash Maps", "Chaining stores colliding entries together; open addressing probes other slots and needs careful load-factor control."),
    ("Heap Invariants", "Heaps", "A heap maintains parent priority over children, enabling O(1) access to the extreme and O(log n) updates."),
    ("Stable Sorting", "Sorting", "A stable sort preserves the relative order of equal keys, which matters when sorting records by multiple fields."),
    ("Recursion and Call Stacks", "Recursion", "Each recursive call owns a frame; define a shrinking subproblem and base case to guarantee termination."),
    ("Greedy Choice Property", "Greedy Algorithms", "A greedy solution needs a locally optimal choice that can be proven compatible with a global optimum."),
    ("Dynamic Programming State Design", "Dynamic Programming", "A DP state must capture all information needed for future decisions without retaining irrelevant history."),
    ("Graph Representation", "Graphs", "Adjacency lists are sparse and iteration-friendly; matrices trade O(V^2) space for constant-time edge checks."),
    ("Union Find", "Graph Algorithms", "Disjoint-set union tracks components efficiently using path compression and union by rank."),
    ("Python Mutability", "Python", "Mutable objects can change in place and shared aliases observe the change; immutable values produce new objects."),
    ("Python Generators", "Python", "Generators suspend execution at yield and produce values lazily, reducing memory for streams."),
    ("Java Garbage Collection", "Java", "The JVM reclaims unreachable objects; collectors balance pause time, throughput, and memory overhead."),
    ("Java equals and hashCode", "Java", "Equal objects must have equal hash codes so hash-based collections can locate them correctly."),
    ("C++ RAII", "C++", "Resource acquisition is tied to object lifetime so destructors release resources reliably on all control paths."),
    ("C++ Smart Pointers", "C++", "unique_ptr expresses sole ownership, shared_ptr reference-counted ownership, and weak_ptr breaks cycles."),
    ("JavaScript Event Loop", "JavaScript", "The call stack runs synchronous work while task queues schedule callbacks; microtasks run before the next task."),
    ("JavaScript Closures", "JavaScript", "A closure retains access to lexical variables after the outer function returns."),
    ("OOP SOLID Principles", "Object-Oriented Programming", "SOLID reduces coupling by clarifying responsibilities, substitution, interfaces, and dependency direction."),
    ("Exception Handling", "Programming Fundamentals", "Catch only errors you can handle, preserve context, and use cleanup constructs for resources."),
    ("Process vs Thread", "Operating Systems", "Processes isolate address spaces; threads share a process address space and need synchronization."),
    ("Deadlock Conditions", "Operating Systems", "Mutual exclusion, hold-and-wait, no preemption, and circular wait are jointly necessary for deadlock."),
    ("Virtual Memory", "Operating Systems", "Virtual memory maps process addresses to physical frames and uses paging to isolate and extend memory."),
    ("Database Indexes", "DBMS", "Indexes accelerate selected reads by maintaining search structures but add storage and write amplification."),
    ("ACID Transactions", "DBMS", "Atomicity, consistency, isolation, and durability define reliable transaction behavior under failures and concurrency."),
    ("SQL Join Selection", "SQL", "INNER JOIN keeps matches; LEFT JOIN preserves every left row; use keys and cardinality deliberately."),
    ("Database Normalization", "DBMS", "Normalization removes update anomalies by separating facts according to functional dependencies."),
    ("TCP vs UDP", "Computer Networks", "TCP provides ordered reliable streams; UDP provides datagrams with lower protocol overhead and no delivery guarantee."),
    ("HTTP Idempotency", "APIs", "Repeating an idempotent operation has the same intended effect, enabling safer retries."),
    ("REST Resource Design", "REST", "REST models stable resources with standard methods, meaningful status codes, and stateless requests."),
    ("Git Rebase vs Merge", "Git", "Merge preserves branch topology; rebase rewrites commits onto a new base for a linear history."),
    ("API Rate Limiting", "APIs", "Token bucket supports bursts while enforcing an average rate and requires a clear distributed consistency strategy."),
    ("Caching Strategies", "System Design", "Cache-aside loads on demand; write-through updates cache and store together; invalidation defines correctness."),
    ("Horizontal Scaling", "System Design", "Horizontal scaling adds instances and requires stateless services or externalized shared state."),
    ("CAP Trade-offs", "Distributed Systems", "During a network partition, a system must choose between guaranteed consistency and guaranteed availability."),
    ("Message Queue Delivery", "Distributed Systems", "At-least-once delivery requires idempotent consumers; ordering and retries must be explicit."),
    ("Cloud Availability Zones", "Cloud Computing", "Distributing replicas across independent zones reduces correlated infrastructure failure."),
    ("Authentication vs Authorization", "Cybersecurity", "Authentication proves identity; authorization decides which actions that identity may perform."),
    ("SQL Injection Prevention", "Cybersecurity", "Parameterized queries separate code from data and should be combined with least privilege and validation."),
    ("Testing Pyramid", "Software Engineering", "Many fast unit tests, fewer integration tests, and focused end-to-end tests balance confidence and speed."),
]


INTERVIEW_TOPICS = [
    ("Tell Me About Yourself", "HR", "Use a present-past-future structure: current strengths, relevant evidence, and why this role is the logical next step."),
    ("Why Should We Hire You", "HR", "Connect three role requirements to specific evidence and explain the value you can create, without comparing yourself negatively to others."),
    ("Why This Company", "HR", "Reference the company's product, engineering challenge, and values, then connect them to your experience and learning goals."),
    ("Strengths", "HR", "Choose a role-relevant strength, prove it with a concise example, and explain how you continue developing it."),
    ("Weaknesses", "HR", "Choose a genuine non-fatal weakness, show self-awareness, and provide concrete actions and measured improvement."),
    ("Five-Year Direction", "HR", "Describe capabilities and impact you want to build rather than promising a specific title you cannot predict."),
    ("Conflict Within a Team", "Behavioral", "Use STAR: explain the disagreement, listen for interests, align on evidence, agree on a decision, and state the result."),
    ("Disagreeing With a Manager", "Situational", "Clarify the goal, present evidence privately, commit after the decision unless it creates ethical or safety risk."),
    ("Missed Deadline", "Behavioral", "Own the miss early, communicate impact, renegotiate scope, remove the root cause, and explain what changed afterward."),
    ("Production Failure", "Situational", "Stabilize users first, establish command and communication, diagnose with evidence, recover safely, then run a blameless review."),
    ("Ambiguous Requirements", "Behavioral", "Identify stakeholders, turn assumptions into questions, define success metrics, and deliver a small feedback-producing slice."),
    ("Leadership Without Authority", "Behavioral", "Build trust through context, invite concerns, create shared ownership, and use evidence rather than hierarchy."),
    ("Challenging Project", "Project", "Explain the goal, your exact ownership, constraints, key decision, measurable result, and what you would improve."),
    ("Project Technology Choice", "Project", "State requirements first, compare realistic alternatives, explain trade-offs, and acknowledge when another choice would be better."),
    ("Project Scaling", "Project", "Start from workload and bottlenecks, then discuss measurement, stateless scaling, data partitioning, caching, and failure handling."),
    ("Project Contribution", "Project", "Separate team outcomes from your decisions, implementation, collaboration, and measurable individual contribution."),
    ("Learning From Failure", "Behavioral", "Choose a real failure, own your part, explain the changed behavior, and prove that the lesson affected later results."),
    ("Prioritizing Competing Work", "Situational", "Compare user impact, urgency, risk, dependencies, and effort; make trade-offs visible to stakeholders."),
    ("Receiving Critical Feedback", "Behavioral", "Listen without defending, clarify examples, agree on an action, and close the loop with evidence of improvement."),
    ("Ethical Concern", "Situational", "Gather facts, identify affected users, document risk, use escalation channels, and refuse unsafe or unlawful action."),
    ("Array and Linked List Trade-offs", "Data Structures and Algorithms", "Discuss access, insertion, memory overhead, cache locality, and workload rather than naming a universal winner."),
    ("Hash Table Design", "Data Structures and Algorithms", "Explain hashing, collision handling, load factor, resizing, and expected versus worst-case complexity."),
    ("Dynamic Programming Recognition", "Data Structures and Algorithms", "Look for repeated subproblems and optimal substructure, then define state, transition, base cases, and evaluation order."),
    ("Graph Traversal Choice", "Data Structures and Algorithms", "BFS suits shortest unweighted paths and levels; DFS suits exhaustive structure, components, and recursion-style exploration."),
    ("Database Transactions", "DBMS", "Explain ACID and isolation anomalies with a practical money-transfer or inventory example."),
    ("SQL Query Optimization", "SQL", "Start with the execution plan, reduce scanned rows, choose indexes from predicates and joins, and measure after each change."),
    ("Operating System Scheduling", "Operating Systems", "Compare fairness, response time, throughput, starvation, and context-switch cost across scheduling policies."),
    ("Deadlock Prevention", "Operating Systems", "Break at least one Coffman condition using ordering, timeouts, preemption where possible, or reduced lock scope."),
    ("TCP Connection", "Computer Networks", "Explain the three-way handshake, sequence synchronization, reliable delivery, congestion control, and connection teardown."),
    ("DNS Resolution", "Computer Networks", "Trace browser and OS caches, recursive resolver, root, TLD, authoritative server, TTL, and final connection."),
    ("Object-Oriented Design", "OOP", "Model responsibilities and collaborations, prefer composition when inheritance does not represent substitution, and protect invariants."),
    ("SOLID in Practice", "Software Engineering", "Use a concrete change scenario to show how focused responsibilities and dependency inversion reduce change impact."),
    ("REST API Design", "APIs", "Define resources, methods, validation, status codes, pagination, idempotency, versioning, authentication, and observability."),
    ("Testing Strategy", "Software Engineering", "Tie tests to risks: pure logic with unit tests, boundaries with integration tests, and critical journeys end to end."),
    ("URL Shortener Design", "System Design", "Clarify scale, generate unique keys, model redirects, cache hot links, partition storage, and handle abuse and expiration."),
    ("Notification System Design", "System Design", "Separate preference, template, scheduling, delivery, provider integration, retry, idempotency, and observability concerns."),
    ("Distributed Consistency", "Distributed Systems", "Explain the business invariant first, then choose strong, eventual, or causal behavior and show conflict handling."),
    ("Microservices Trade-offs", "Distributed Systems", "Balance independent deployment and team ownership against network failure, data consistency, and operational complexity."),
    ("Cloud Deployment", "Cloud Computing", "Cover immutable artifacts, configuration, health checks, staged rollout, observability, rollback, and multi-zone resilience."),
    ("Secure API", "Cybersecurity", "Use TLS, strong identity, least privilege, input validation, rate limits, secret management, audit logs, and safe errors."),
    ("Machine Learning Workflow", "AI/ML", "Frame the objective and metric, establish a baseline, prepare leakage-safe data, train, evaluate slices, deploy, and monitor."),
    ("Bias and Variance", "AI/ML", "High bias underfits; high variance overfits. Diagnose train-validation behavior before changing capacity, data, or regularization."),
    ("Overfitting", "Machine Learning", "Overfitting memorizes training-specific noise; address it with validation, simpler models, regularization, augmentation, and more representative data."),
    ("Classification Metrics", "Machine Learning", "Choose precision, recall, F1, PR-AUC, ROC-AUC, and calibration based on error costs and class balance."),
    ("Feature Engineering", "Machine Learning", "Encode domain signal without leakage, make transformations reproducible, and validate contribution through controlled experiments."),
    ("Neural Network Backpropagation", "Deep Learning", "Backpropagation applies the chain rule from loss to parameters; optimizers use those gradients to update weights."),
    ("CNN Architecture", "Computer Vision", "Convolutions exploit local spatial structure and weight sharing; receptive field, stride, padding, and pooling shape representation."),
    ("RNN and LSTM", "Deep Learning", "LSTM gates create controlled memory paths that reduce, but do not eliminate, long-range gradient problems in sequence models."),
    ("Transformer Attention", "Transformers", "Self-attention forms content-dependent weighted combinations using queries, keys, and values, enabling parallel context mixing."),
    ("LLM Evaluation", "Large Language Models", "Combine task-specific automatic metrics, human rubrics, adversarial sets, safety checks, latency, cost, and regression gates."),
    ("Prompt Engineering", "Generative AI", "Specify task, context, constraints, output format, and examples; evaluate prompts against a representative fixed set."),
    ("Retrieval-Augmented Generation", "RAG", "Retrieve relevant evidence, manage chunking and ranking, ground generation, cite sources, and evaluate retrieval separately from generation."),
    ("Embeddings", "AI/ML", "Embeddings map items into vectors where useful similarity becomes geometric proximity; quality depends on objective, data, and distance metric."),
    ("Vector Databases", "RAG", "Explain approximate nearest-neighbour indexes, metadata filtering, recall-latency trade-offs, updates, and access control."),
    ("Fine-Tuning vs Prompting", "Large Language Models", "Use prompting for instruction and context changes; fine-tune for stable behavior patterns after measuring a clear gap."),
    ("MLOps Monitoring", "MLOps", "Monitor service health, input drift, prediction distributions, delayed outcomes, slice performance, and retraining triggers."),
    ("Recommendation Systems", "AI/ML", "Separate candidate generation and ranking, define feedback labels carefully, address cold start, and evaluate offline plus online."),
    ("Model Deployment", "MLOps", "Package preprocessing with the model, version artifacts, validate compatibility, canary traffic, monitor, and preserve rollback."),
    ("Responsible AI", "AI/ML", "Identify affected groups and harms, test performance slices, control data and access, document limitations, and add human escalation."),
    ("Pandas Data Pipeline", "Python for AI", "Use vectorized transformations, explicit schemas, reproducible missing-value handling, and validation checkpoints instead of row-wise hidden state."),
]


def _base_record(question_id, question_type, category, subcategory, company, difficulty, question,
                 answer, explanation, example, tags, topic, frequency, **extras):
    return {
        "id": question_id,
        "question_type": question_type,
        "category": category,
        "subcategory": subcategory,
        "company": company,
        "difficulty": difficulty,
        "question": question,
        "answer": answer,
        "detailed_explanation": explanation,
        "example": example,
        "tags_json": safe_json_dumps(tags),
        "topic": topic,
        "estimated_study_time": extras.get("estimated_study_time", 6),
        "frequency": frequency,
        "related_questions_json": "[]",
        "approach": extras.get("approach", ""),
        "code": extras.get("code", ""),
        "time_complexity": extras.get("time_complexity", ""),
        "space_complexity": extras.get("space_complexity", ""),
        "common_mistakes": extras.get("common_mistakes", ""),
        "interview_tip": extras.get("interview_tip", "Explain assumptions and reasoning before giving the final answer."),
    }


def build_aptitude_learning_questions(aptitude_rows):
    records = []
    for index, row in enumerate(aptitude_rows):
        options = safe_json_loads(row["options_json"], [])
        topic = row["category"]
        records.append(
            _base_record(
                f"learn-apt-{row['id']:03d}", "aptitude", row["category"], row["category"],
                row["company"], row["difficulty"], row["question"], row["answer"],
                f"Work from the information given, choose the relevant rule, and compute or deduce each step. {row['explanation']} Check the result against the choices before committing.",
                "Options: " + " | ".join(options), [topic, "Aptitude", row["company"]], topic,
                FREQUENCIES[index % len(FREQUENCIES)], estimated_study_time=4,
                common_mistakes="Rushing the arithmetic, assuming facts not stated, or selecting an option without verifying the final step.",
                interview_tip="State the formula or logical rule first, then calculate cleanly so the evaluator can follow your method.",
            )
        )
    return records


def build_coding_learning_questions():
    records = []
    angles = [
        ("implementation", "Implement {name} and explain the invariant that keeps the solution correct."),
        ("approach", "For {name}, compare a straightforward approach with the optimized strategy you would present in an interview."),
        ("edge-cases", "Which edge cases can break a solution to {name}, and how should the implementation handle them?"),
        ("debugging", "A candidate's {name} solution passes common examples but fails hidden tests. Describe a systematic debugging plan."),
        ("complexity", "Derive the time and space complexity of the preferred solution for {name}."),
        ("scale", "How would you adapt {name} when the input is too large to fit comfortably in memory?"),
        ("testing", "Design a compact but high-value test suite for {name}."),
        ("follow-up", "What follow-up variation would make {name} harder, and how would your solution change?"),
    ]
    for problem_index, (name, topic, strategy, time_cost, space_cost, example, code) in enumerate(CODING_PROBLEMS):
        for angle_index, (angle, prompt) in enumerate(angles):
            item_index = problem_index * len(angles) + angle_index
            company = COMPANIES[item_index % len(COMPANIES)]
            difficulty = DIFFICULTIES[(problem_index + angle_index) % 3]
            answer = (
                f"Preferred strategy: {strategy} The key is to state the maintained invariant, prove why each update preserves it, "
                f"and test boundary inputs before discussing optimization. Reference complexity is {time_cost} time and {space_cost} space."
            )
            explanation = (
                f"Start by translating the requirement into a precise input-output contract. For {name}, {strategy.lower()} "
                "A strong explanation connects the data structure to the required operations, walks through one example, "
                "and then discusses edge cases and alternatives. For the selected learning angle, focus on " + angle.replace("-", " ") + "."
            )
            records.append(
                _base_record(
                    f"learn-code-{item_index + 1:03d}", "coding", "Coding", topic, company, difficulty,
                    prompt.format(name=name), answer, explanation, example,
                    [topic, "Algorithms", "Python", "Java", "C++", "JavaScript", angle], topic,
                    FREQUENCIES[item_index % len(FREQUENCIES)], estimated_study_time=10,
                    approach=strategy, code=code, time_complexity=time_cost, space_complexity=space_cost,
                    common_mistakes="Skipping input clarification, losing an invariant during updates, ignoring empty or duplicate values, or claiming complexity without deriving it.",
                    interview_tip="Explain the brute-force baseline briefly, then motivate the optimized data structure before writing code.",
                )
            )

    concept_angles = [
        "Explain {name} to an interviewer using a concrete engineering example.",
        "When would you choose {name}, and when would it be the wrong choice?",
        "What common implementation or design mistake occurs with {name}, and how do you prevent it?",
        "How does {name} behave under scale, concurrency, or failure?",
        "Design a small test or experiment that demonstrates the important property of {name}.",
    ]
    start_index = len(records)
    for concept_index, (name, topic, core) in enumerate(TECHNICAL_CONCEPTS):
        for angle_index, prompt in enumerate(concept_angles):
            item_index = start_index + concept_index * len(concept_angles) + angle_index
            company = COMPANIES[item_index % len(COMPANIES)]
            answer = f"Core idea: {core} A good decision starts from workload, correctness needs, and operational constraints rather than preference."
            explanation = (
                f"{name} matters because it changes correctness, performance, or maintainability. {core} "
                "In an interview, define the concept, show a realistic example, name the trade-off, and identify one failure mode or measurement."
            )
            records.append(
                _base_record(
                    f"learn-code-{item_index + 1:03d}", "coding", "Computer Science", topic, company,
                    DIFFICULTIES[(concept_index + angle_index) % 3], prompt.format(name=name), answer,
                    explanation, f"Apply {name} to a production service or a small program and compare expected behavior before and after.",
                    [topic, name, "Computer Science", "Software Engineering"], name,
                    FREQUENCIES[item_index % len(FREQUENCIES)], estimated_study_time=7,
                    common_mistakes="Giving only a definition, ignoring trade-offs, or failing to connect the concept to observable system behavior.",
                    interview_tip="Use definition, example, trade-off, and failure mode as a four-part answer structure.",
                )
            )
    if len(records) != 400:
        raise RuntimeError(f"Coding catalog must contain 400 questions, found {len(records)}.")
    return records


def build_interview_learning_questions():
    records = []
    angles = [
        "Give a strong interview answer for: {name}.",
        "What does an interviewer evaluate when asking about {name}, and how should a candidate structure the response?",
        "Provide a weak answer to {name}, identify its problems, and improve it.",
        "Answer a follow-up that challenges an assumption in your response about {name}.",
        "Create a concise real-world example that demonstrates {name} effectively.",
    ]
    for topic_index, (name, category, guidance) in enumerate(INTERVIEW_TOPICS):
        for angle_index, prompt in enumerate(angles):
            item_index = topic_index * len(angles) + angle_index
            company = COMPANIES[item_index % len(COMPANIES)]
            behavioral = category in {"HR", "Behavioral", "Situational", "Project"}
            framework = (
                "Use STAR where evidence is needed: Situation sets only necessary context, Task states your responsibility, "
                "Action shows your decisions, and Result includes impact and learning. " if behavioral else
                "Use a definition-example-trade-off structure, then connect the concept to a production or project decision. "
            )
            answer = f"{framework}{guidance} Keep the response direct, evidence-based, and honest about constraints."
            explanation = (
                f"The interviewer is testing clarity, judgment, and depth rather than memorized wording. {guidance} "
                "A strong response explains why the decision makes sense, acknowledges alternatives, and gives the interviewer a clear follow-up path."
            )
            records.append(
                _base_record(
                    f"learn-int-{item_index + 1:03d}", "interview", category, category, company,
                    DIFFICULTIES[(topic_index + angle_index) % 3], prompt.format(name=name), answer,
                    explanation, f"Example outline: context -> key decision for {name} -> evidence or trade-off -> result -> learning.",
                    [category, name, "Interview", "STAR" if behavioral else "Technical"], name,
                    FREQUENCIES[item_index % len(FREQUENCIES)], estimated_study_time=7,
                    common_mistakes="Giving a generic answer, hiding individual ownership, overloading context, or making claims without evidence.",
                    interview_tip="Pause, state your structure aloud, and keep the most important decision and result easy to identify.",
                )
            )
    if len(records) != 300:
        raise RuntimeError(f"Interview catalog must contain 300 questions, found {len(records)}.")
    return records


def generate_learning_catalog(aptitude_rows):
    records = [
        *build_aptitude_learning_questions(aptitude_rows),
        *build_coding_learning_questions(),
        *build_interview_learning_questions(),
    ]
    if len(records) != 1000 or len({record["id"] for record in records}) != 1000:
        raise RuntimeError("Learning catalog must contain exactly 1,000 unique question IDs.")
    if len({record["question"] for record in records}) != 1000:
        raise RuntimeError("Learning catalog question text must be unique.")
    required = {"id", "question_type", "category", "company", "difficulty", "question", "answer", "detailed_explanation", "topic"}
    if any(not required.issubset(record) or any(not record[key] for key in required) for record in records):
        raise RuntimeError("Learning catalog contains an incomplete question.")
    return records
