"""Curated practical coding exercises for the Interview Learning module.

The catalog is generated from tested algorithm families and distinct application
contexts. Keeping the source structured makes the 200-question bank easy to
validate, extend, and seed without shipping a large static JSON payload.
"""

from interview_simulator.utils.common import safe_json_dumps


PRACTICAL_COMPANIES = [
    "Alphabet (Google)", "Microsoft", "Amazon", "Apple", "NVIDIA", "Meta", "Adobe",
    "Oracle", "IBM", "Walmart", "Flipkart", "Atlassian", "Uber", "Goldman Sachs",
    "Morgan Stanley", "JPMorgan Chase", "Salesforce", "Intel", "Cisco", "Accenture",
]


def _solution_library():
    """Return compact, executable reference solutions in four languages."""
    return {
        "two_sum": {
            "python": """def find_pair(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        complement = target - value
        if complement in seen:
            return [seen[complement], index]
        seen[value] = index
    return []""",
            "java": """import java.util.*;
class Solution {
    static int[] findPair(int[] nums, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) return new int[]{seen.get(complement), i};
            seen.put(nums[i], i);
        }
        return new int[0];
    }
}""",
            "cpp": """#include <unordered_map>
#include <vector>
using namespace std;
vector<int> findPair(const vector<int>& nums, int target) {
    unordered_map<int, int> seen;
    for (int i = 0; i < (int)nums.size(); ++i) {
        int complement = target - nums[i];
        if (seen.count(complement)) return {seen[complement], i};
        seen[nums[i]] = i;
    }
    return {};
}""",
            "javascript": """function findPair(nums, target) {
  const seen = new Map();
  for (let index = 0; index < nums.length; index += 1) {
    const complement = target - nums[index];
    if (seen.has(complement)) return [seen.get(complement), index];
    seen.set(nums[index], index);
  }
  return [];
}""",
        },
        "longest_unique": {
            "python": """def longest_unique(text):
    last, left, best = {}, 0, 0
    for right, char in enumerate(text):
        left = max(left, last.get(char, -1) + 1)
        last[char] = right
        best = max(best, right - left + 1)
    return best""",
            "java": """import java.util.*;
class Solution {
    static int longestUnique(String text) {
        Map<Character, Integer> last = new HashMap<>();
        int left = 0, best = 0;
        for (int right = 0; right < text.length(); right++) {
            char ch = text.charAt(right);
            left = Math.max(left, last.getOrDefault(ch, -1) + 1);
            last.put(ch, right);
            best = Math.max(best, right - left + 1);
        }
        return best;
    }
}""",
            "cpp": """#include <algorithm>
#include <string>
#include <unordered_map>
using namespace std;
int longestUnique(const string& text) {
    unordered_map<char, int> last;
    int left = 0, best = 0;
    for (int right = 0; right < (int)text.size(); ++right) {
        if (last.count(text[right])) left = max(left, last[text[right]] + 1);
        last[text[right]] = right;
        best = max(best, right - left + 1);
    }
    return best;
}""",
            "javascript": """function longestUnique(text) {
  const last = new Map();
  let left = 0;
  let best = 0;
  for (let right = 0; right < text.length; right += 1) {
    left = Math.max(left, (last.get(text[right]) ?? -1) + 1);
    last.set(text[right], right);
    best = Math.max(best, right - left + 1);
  }
  return best;
}""",
        },
        "reverse_list": {
            "python": """class ListNode:
    def __init__(self, value=0, next_node=None):
        self.value, self.next = value, next_node

def reverse_list(head):
    previous = None
    while head:
        following = head.next
        head.next = previous
        previous, head = head, following
    return previous""",
            "java": """class ListNode {
    int value; ListNode next;
    ListNode(int value) { this.value = value; }
}
class Solution {
    static ListNode reverseList(ListNode head) {
        ListNode previous = null;
        while (head != null) {
            ListNode following = head.next;
            head.next = previous;
            previous = head;
            head = following;
        }
        return previous;
    }
}""",
            "cpp": """struct ListNode {
    int value;
    ListNode* next;
    explicit ListNode(int value) : value(value), next(nullptr) {}
};
ListNode* reverseList(ListNode* head) {
    ListNode* previous = nullptr;
    while (head) {
        ListNode* following = head->next;
        head->next = previous;
        previous = head;
        head = following;
    }
    return previous;
}""",
            "javascript": """class ListNode {
  constructor(value, next = null) { this.value = value; this.next = next; }
}
function reverseList(head) {
  let previous = null;
  while (head) {
    const following = head.next;
    head.next = previous;
    previous = head;
    head = following;
  }
  return previous;
}""",
        },
        "valid_brackets": {
            "python": """def valid_brackets(text):
    pairs, stack = {')': '(', ']': '[', '}': '{'}, []
    for char in text:
        if char in '([{':
            stack.append(char)
        elif char in pairs and (not stack or stack.pop() != pairs[char]):
            return False
    return not stack""",
            "java": """import java.util.*;
class Solution {
    static boolean validBrackets(String text) {
        Map<Character, Character> pairs = Map.of(')', '(', ']', '[', '}', '{');
        Deque<Character> stack = new ArrayDeque<>();
        for (char ch : text.toCharArray()) {
            if (ch == '(' || ch == '[' || ch == '{') stack.push(ch);
            else if (pairs.containsKey(ch) && (stack.isEmpty() || stack.pop() != pairs.get(ch))) return false;
        }
        return stack.isEmpty();
    }
}""",
            "cpp": """#include <stack>
#include <string>
#include <unordered_map>
using namespace std;
bool validBrackets(const string& text) {
    unordered_map<char, char> pairs{{')','('},{']','['},{'}','{'}};
    stack<char> open;
    for (char ch : text) {
        if (ch == '(' || ch == '[' || ch == '{') open.push(ch);
        else if (pairs.count(ch)) {
            if (open.empty() || open.top() != pairs[ch]) return false;
            open.pop();
        }
    }
    return open.empty();
}""",
            "javascript": """function validBrackets(text) {
  const pairs = { ')': '(', ']': '[', '}': '{' };
  const stack = [];
  for (const char of text) {
    if ('([{'.includes(char)) stack.push(char);
    else if (pairs[char] && stack.pop() !== pairs[char]) return false;
  }
  return stack.length === 0;
}""",
        },
        "window_max": {
            "python": """from collections import deque
def window_maximum(nums, size):
    queue, result = deque(), []
    for index, value in enumerate(nums):
        while queue and queue[0] <= index - size: queue.popleft()
        while queue and nums[queue[-1]] <= value: queue.pop()
        queue.append(index)
        if index >= size - 1: result.append(nums[queue[0]])
    return result""",
            "java": """import java.util.*;
class Solution {
    static int[] windowMaximum(int[] nums, int size) {
        Deque<Integer> queue = new ArrayDeque<>();
        int[] result = new int[nums.length - size + 1];
        for (int i = 0; i < nums.length; i++) {
            while (!queue.isEmpty() && queue.peekFirst() <= i - size) queue.removeFirst();
            while (!queue.isEmpty() && nums[queue.peekLast()] <= nums[i]) queue.removeLast();
            queue.addLast(i);
            if (i >= size - 1) result[i - size + 1] = nums[queue.peekFirst()];
        }
        return result;
    }
}""",
            "cpp": """#include <deque>
#include <vector>
using namespace std;
vector<int> windowMaximum(const vector<int>& nums, int size) {
    deque<int> queue;
    vector<int> result;
    for (int i = 0; i < (int)nums.size(); ++i) {
        while (!queue.empty() && queue.front() <= i - size) queue.pop_front();
        while (!queue.empty() && nums[queue.back()] <= nums[i]) queue.pop_back();
        queue.push_back(i);
        if (i >= size - 1) result.push_back(nums[queue.front()]);
    }
    return result;
}""",
            "javascript": """function windowMaximum(nums, size) {
  const queue = [];
  const result = [];
  for (let index = 0; index < nums.length; index += 1) {
    while (queue.length && queue[0] <= index - size) queue.shift();
    while (queue.length && nums[queue.at(-1)] <= nums[index]) queue.pop();
    queue.push(index);
    if (index >= size - 1) result.push(nums[queue[0]]);
  }
  return result;
}""",
        },
        "group_anagrams": {
            "python": """from collections import defaultdict
def group_anagrams(words):
    groups = defaultdict(list)
    for word in words:
        groups[''.join(sorted(word))].append(word)
    return list(groups.values())""",
            "java": """import java.util.*;
class Solution {
    static List<List<String>> groupAnagrams(String[] words) {
        Map<String, List<String>> groups = new LinkedHashMap<>();
        for (String word : words) {
            char[] chars = word.toCharArray(); Arrays.sort(chars);
            groups.computeIfAbsent(new String(chars), key -> new ArrayList<>()).add(word);
        }
        return new ArrayList<>(groups.values());
    }
}""",
            "cpp": """#include <algorithm>
#include <string>
#include <unordered_map>
#include <vector>
using namespace std;
vector<vector<string>> groupAnagrams(const vector<string>& words) {
    unordered_map<string, vector<string>> groups;
    for (const string& word : words) {
        string key = word; sort(key.begin(), key.end());
        groups[key].push_back(word);
    }
    vector<vector<string>> result;
    for (auto& entry : groups) result.push_back(entry.second);
    return result;
}""",
            "javascript": """function groupAnagrams(words) {
  const groups = new Map();
  for (const word of words) {
    const key = [...word].sort().join('');
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(word);
  }
  return [...groups.values()];
}""",
        },
        "level_order": {
            "python": """from collections import deque
def level_order(root):
    if not root: return []
    queue, levels = deque([root]), []
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft(); level.append(node.value)
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        levels.append(level)
    return levels""",
            "java": """import java.util.*;
class TreeNode { int value; TreeNode left, right; TreeNode(int v) { value = v; } }
class Solution {
    static List<List<Integer>> levelOrder(TreeNode root) {
        List<List<Integer>> levels = new ArrayList<>();
        if (root == null) return levels;
        Queue<TreeNode> queue = new ArrayDeque<>(); queue.add(root);
        while (!queue.isEmpty()) {
            List<Integer> level = new ArrayList<>(); int size = queue.size();
            while (size-- > 0) { TreeNode node = queue.remove(); level.add(node.value); if (node.left != null) queue.add(node.left); if (node.right != null) queue.add(node.right); }
            levels.add(level);
        }
        return levels;
    }
}""",
            "cpp": """#include <queue>
#include <vector>
using namespace std;
struct TreeNode { int value; TreeNode *left, *right; };
vector<vector<int>> levelOrder(TreeNode* root) {
    if (!root) return {};
    queue<TreeNode*> nodes; nodes.push(root);
    vector<vector<int>> levels;
    while (!nodes.empty()) {
        vector<int> level; int size = nodes.size();
        while (size--) { auto node = nodes.front(); nodes.pop(); level.push_back(node->value); if (node->left) nodes.push(node->left); if (node->right) nodes.push(node->right); }
        levels.push_back(level);
    }
    return levels;
}""",
            "javascript": """function levelOrder(root) {
  if (!root) return [];
  const queue = [root];
  const levels = [];
  while (queue.length) {
    const level = [];
    for (let count = queue.length; count > 0; count -= 1) {
      const node = queue.shift(); level.push(node.value);
      if (node.left) queue.push(node.left); if (node.right) queue.push(node.right);
    }
    levels.push(level);
  }
  return levels;
}""",
        },
        "valid_bst": {
            "python": """def valid_bst(root):
    def check(node, low, high):
        if not node: return True
        if not low < node.value < high: return False
        return check(node.left, low, node.value) and check(node.right, node.value, high)
    return check(root, float('-inf'), float('inf'))""",
            "java": """class TreeNode { int value; TreeNode left, right; TreeNode(int v) { value = v; } }
class Solution {
    static boolean validBst(TreeNode root) { return check(root, Long.MIN_VALUE, Long.MAX_VALUE); }
    static boolean check(TreeNode node, long low, long high) {
        if (node == null) return true;
        if (node.value <= low || node.value >= high) return false;
        return check(node.left, low, node.value) && check(node.right, node.value, high);
    }
}""",
            "cpp": """#include <climits>
struct TreeNode { int value; TreeNode *left, *right; };
bool check(TreeNode* node, long long low, long long high) {
    if (!node) return true;
    if (node->value <= low || node->value >= high) return false;
    return check(node->left, low, node->value) && check(node->right, node->value, high);
}
bool validBst(TreeNode* root) { return check(root, LLONG_MIN, LLONG_MAX); }""",
            "javascript": """function validBst(root) {
  function check(node, low, high) {
    if (!node) return true;
    if (node.value <= low || node.value >= high) return false;
    return check(node.left, low, node.value) && check(node.right, node.value, high);
  }
  return check(root, -Infinity, Infinity);
}""",
        },
        "components": {
            "python": """def connected_components(graph):
    visited, count = set(), 0
    for start in graph:
        if start in visited: continue
        count += 1
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited: continue
            visited.add(node)
            stack.extend(graph[node])
    return count""",
            "java": """import java.util.*;
class Solution {
    static int connectedComponents(Map<Integer, List<Integer>> graph) {
        Set<Integer> visited = new HashSet<>(); int count = 0;
        for (int start : graph.keySet()) {
            if (visited.contains(start)) continue;
            count++; Deque<Integer> stack = new ArrayDeque<>(); stack.push(start);
            while (!stack.isEmpty()) { int node = stack.pop(); if (!visited.add(node)) continue; for (int next : graph.getOrDefault(node, List.of())) stack.push(next); }
        }
        return count;
    }
}""",
            "cpp": """#include <stack>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using namespace std;
int connectedComponents(const unordered_map<int, vector<int>>& graph) {
    unordered_set<int> visited; int count = 0;
    for (const auto& entry : graph) {
        if (visited.count(entry.first)) continue;
        ++count; stack<int> pending; pending.push(entry.first);
        while (!pending.empty()) { int node = pending.top(); pending.pop(); if (!visited.insert(node).second) continue; for (int next : graph.at(node)) pending.push(next); }
    }
    return count;
}""",
            "javascript": """function connectedComponents(graph) {
  const visited = new Set();
  let count = 0;
  for (const start of graph.keys()) {
    if (visited.has(start)) continue;
    count += 1;
    const stack = [start];
    while (stack.length) {
      const node = stack.pop(); if (visited.has(node)) continue;
      visited.add(node); stack.push(...(graph.get(node) ?? []));
    }
  }
  return count;
}""",
        },
        "merge_intervals": {
            "python": """def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result""",
            "java": """import java.util.*;
class Solution {
    static int[][] mergeIntervals(int[][] intervals) {
        Arrays.sort(intervals, Comparator.comparingInt(item -> item[0]));
        List<int[]> result = new ArrayList<>();
        for (int[] interval : intervals) {
            if (!result.isEmpty() && interval[0] <= result.get(result.size() - 1)[1]) result.get(result.size() - 1)[1] = Math.max(result.get(result.size() - 1)[1], interval[1]);
            else result.add(interval.clone());
        }
        return result.toArray(new int[0][]);
    }
}""",
            "cpp": """#include <algorithm>
#include <vector>
using namespace std;
vector<vector<int>> mergeIntervals(vector<vector<int>> intervals) {
    sort(intervals.begin(), intervals.end());
    vector<vector<int>> result;
    for (const auto& interval : intervals) {
        if (!result.empty() && interval[0] <= result.back()[1]) result.back()[1] = max(result.back()[1], interval[1]);
        else result.push_back(interval);
    }
    return result;
}""",
            "javascript": """function mergeIntervals(intervals) {
  intervals.sort((a, b) => a[0] - b[0]);
  const result = [];
  for (const interval of intervals) {
    if (result.length && interval[0] <= result.at(-1)[1]) result.at(-1)[1] = Math.max(result.at(-1)[1], interval[1]);
    else result.push([...interval]);
  }
  return result;
}""",
        },
        "binary_search": {
            "python": """def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        middle = left + (right - left) // 2
        if nums[middle] == target: return middle
        if nums[middle] < target: left = middle + 1
        else: right = middle - 1
    return -1""",
            "java": """class Solution {
    static int binarySearch(int[] nums, int target) {
        int left = 0, right = nums.length - 1;
        while (left <= right) {
            int middle = left + (right - left) / 2;
            if (nums[middle] == target) return middle;
            if (nums[middle] < target) left = middle + 1; else right = middle - 1;
        }
        return -1;
    }
}""",
            "cpp": """#include <vector>
using namespace std;
int binarySearch(const vector<int>& nums, int target) {
    int left = 0, right = (int)nums.size() - 1;
    while (left <= right) {
        int middle = left + (right - left) / 2;
        if (nums[middle] == target) return middle;
        if (nums[middle] < target) left = middle + 1; else right = middle - 1;
    }
    return -1;
}""",
            "javascript": """function binarySearch(nums, target) {
  let left = 0;
  let right = nums.length - 1;
  while (left <= right) {
    const middle = left + Math.floor((right - left) / 2);
    if (nums[middle] === target) return middle;
    if (nums[middle] < target) left = middle + 1; else right = middle - 1;
  }
  return -1;
}""",
        },
        "subsets": {
            "python": """def subsets(nums):
    result = [[]]
    for value in nums:
        result += [current + [value] for current in result]
    return result""",
            "java": """import java.util.*;
class Solution {
    static List<List<Integer>> subsets(int[] nums) {
        List<List<Integer>> result = new ArrayList<>(); result.add(new ArrayList<>());
        for (int value : nums) {
            int size = result.size();
            for (int i = 0; i < size; i++) { List<Integer> next = new ArrayList<>(result.get(i)); next.add(value); result.add(next); }
        }
        return result;
    }
}""",
            "cpp": """#include <vector>
using namespace std;
vector<vector<int>> subsets(const vector<int>& nums) {
    vector<vector<int>> result{{}};
    for (int value : nums) {
        int size = result.size();
        for (int i = 0; i < size; ++i) { auto next = result[i]; next.push_back(value); result.push_back(next); }
    }
    return result;
}""",
            "javascript": """function subsets(nums) {
  const result = [[]];
  for (const value of nums) {
    const current = result.map((item) => [...item, value]);
    result.push(...current);
  }
  return result;
}""",
        },
        "coin_change": {
            "python": """def coin_change(coins, amount):
    dp = [0] + [amount + 1] * amount
    for value in range(1, amount + 1):
        for coin in coins:
            if coin <= value: dp[value] = min(dp[value], dp[value - coin] + 1)
    return dp[amount] if dp[amount] <= amount else -1""",
            "java": """import java.util.*;
class Solution {
    static int coinChange(int[] coins, int amount) {
        int[] dp = new int[amount + 1]; Arrays.fill(dp, amount + 1); dp[0] = 0;
        for (int value = 1; value <= amount; value++) for (int coin : coins) if (coin <= value) dp[value] = Math.min(dp[value], dp[value - coin] + 1);
        return dp[amount] <= amount ? dp[amount] : -1;
    }
}""",
            "cpp": """#include <algorithm>
#include <vector>
using namespace std;
int coinChange(const vector<int>& coins, int amount) {
    vector<int> dp(amount + 1, amount + 1); dp[0] = 0;
    for (int value = 1; value <= amount; ++value) for (int coin : coins) if (coin <= value) dp[value] = min(dp[value], dp[value - coin] + 1);
    return dp[amount] <= amount ? dp[amount] : -1;
}""",
            "javascript": """function coinChange(coins, amount) {
  const dp = Array(amount + 1).fill(amount + 1); dp[0] = 0;
  for (let value = 1; value <= amount; value += 1) {
    for (const coin of coins) if (coin <= value) dp[value] = Math.min(dp[value], dp[value - coin] + 1);
  }
  return dp[amount] <= amount ? dp[amount] : -1;
}""",
        },
        "activity_selection": {
            "python": """def maximum_non_overlapping(intervals):
    selected, last_end = [], float('-inf')
    for start, end in sorted(intervals, key=lambda item: item[1]):
        if start >= last_end:
            selected.append([start, end]); last_end = end
    return selected""",
            "java": """import java.util.*;
class Solution {
    static List<int[]> maximumNonOverlapping(int[][] intervals) {
        Arrays.sort(intervals, Comparator.comparingInt(item -> item[1]));
        List<int[]> selected = new ArrayList<>(); int lastEnd = Integer.MIN_VALUE;
        for (int[] item : intervals) if (item[0] >= lastEnd) { selected.add(item); lastEnd = item[1]; }
        return selected;
    }
}""",
            "cpp": """#include <algorithm>
#include <climits>
#include <vector>
using namespace std;
vector<vector<int>> maximumNonOverlapping(vector<vector<int>> intervals) {
    sort(intervals.begin(), intervals.end(), [](auto& a, auto& b) { return a[1] < b[1]; });
    vector<vector<int>> selected; int lastEnd = INT_MIN;
    for (auto& item : intervals) if (item[0] >= lastEnd) { selected.push_back(item); lastEnd = item[1]; }
    return selected;
}""",
            "javascript": """function maximumNonOverlapping(intervals) {
  intervals.sort((a, b) => a[1] - b[1]);
  const selected = [];
  let lastEnd = -Infinity;
  for (const item of intervals) if (item[0] >= lastEnd) { selected.push(item); lastEnd = item[1]; }
  return selected;
}""",
        },
        "window_sum": {
            "python": """def maximum_window_sum(nums, size):
    if size <= 0 or size > len(nums): raise ValueError('invalid window size')
    current = sum(nums[:size]); best = current
    for index in range(size, len(nums)):
        current += nums[index] - nums[index - size]
        best = max(best, current)
    return best""",
            "java": """class Solution {
    static long maximumWindowSum(int[] nums, int size) {
        if (size <= 0 || size > nums.length) throw new IllegalArgumentException();
        long current = 0; for (int i = 0; i < size; i++) current += nums[i];
        long best = current;
        for (int i = size; i < nums.length; i++) { current += nums[i] - nums[i - size]; best = Math.max(best, current); }
        return best;
    }
}""",
            "cpp": """#include <algorithm>
#include <stdexcept>
#include <vector>
using namespace std;
long long maximumWindowSum(const vector<int>& nums, int size) {
    if (size <= 0 || size > (int)nums.size()) throw invalid_argument("invalid window size");
    long long current = 0; for (int i = 0; i < size; ++i) current += nums[i];
    long long best = current;
    for (int i = size; i < (int)nums.size(); ++i) { current += nums[i] - nums[i-size]; best = max(best, current); }
    return best;
}""",
            "javascript": """function maximumWindowSum(nums, size) {
  if (size <= 0 || size > nums.length) throw new Error('invalid window size');
  let current = nums.slice(0, size).reduce((sum, value) => sum + value, 0);
  let best = current;
  for (let index = size; index < nums.length; index += 1) { current += nums[index] - nums[index - size]; best = Math.max(best, current); }
  return best;
}""",
        },
        "sorted_pair": {
            "python": """def sorted_pair_sum(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        total = nums[left] + nums[right]
        if total == target: return [left, right]
        if total < target: left += 1
        else: right -= 1
    return []""",
            "java": """class Solution {
    static int[] sortedPairSum(int[] nums, int target) {
        int left = 0, right = nums.length - 1;
        while (left < right) {
            int total = nums[left] + nums[right];
            if (total == target) return new int[]{left, right};
            if (total < target) left++; else right--;
        }
        return new int[0];
    }
}""",
            "cpp": """#include <vector>
using namespace std;
vector<int> sortedPairSum(const vector<int>& nums, int target) {
    int left = 0, right = (int)nums.size() - 1;
    while (left < right) {
        int total = nums[left] + nums[right];
        if (total == target) return {left, right};
        if (total < target) ++left; else --right;
    }
    return {};
}""",
            "javascript": """function sortedPairSum(nums, target) {
  let left = 0;
  let right = nums.length - 1;
  while (left < right) {
    const total = nums[left] + nums[right];
    if (total === target) return [left, right];
    if (total < target) left += 1; else right -= 1;
  }
  return [];
}""",
        },
        "kth_largest": {
            "python": """import heapq
def kth_largest(nums, k):
    heap = []
    for value in nums:
        heapq.heappush(heap, value)
        if len(heap) > k: heapq.heappop(heap)
    return heap[0]""",
            "java": """import java.util.*;
class Solution {
    static int kthLargest(int[] nums, int k) {
        PriorityQueue<Integer> heap = new PriorityQueue<>();
        for (int value : nums) { heap.add(value); if (heap.size() > k) heap.remove(); }
        return heap.element();
    }
}""",
            "cpp": """#include <functional>
#include <queue>
#include <vector>
using namespace std;
int kthLargest(const vector<int>& nums, int k) {
    priority_queue<int, vector<int>, greater<int>> heap;
    for (int value : nums) { heap.push(value); if ((int)heap.size() > k) heap.pop(); }
    return heap.top();
}""",
            "javascript": """function kthLargest(nums, k) {
  const ordered = [...nums].sort((a, b) => b - a);
  return ordered[k - 1];
}""",
        },
        "single_number": {
            "python": """def single_number(nums):
    unique = 0
    for value in nums: unique ^= value
    return unique""",
            "java": """class Solution {
    static int singleNumber(int[] nums) {
        int unique = 0;
        for (int value : nums) unique ^= value;
        return unique;
    }
}""",
            "cpp": """#include <vector>
using namespace std;
int singleNumber(const vector<int>& nums) {
    int unique = 0;
    for (int value : nums) unique ^= value;
    return unique;
}""",
            "javascript": """function singleNumber(nums) {
  let unique = 0;
  for (const value of nums) unique ^= value;
  return unique;
}""",
        },
        "spiral": {
            "python": """def spiral_order(matrix):
    result = []
    while matrix:
        result += matrix.pop(0)
        if matrix and matrix[0]:
            for row in matrix: result.append(row.pop())
        if matrix: result += matrix.pop()[::-1]
        if matrix and matrix[0]:
            for row in matrix[::-1]: result.append(row.pop(0))
    return result""",
            "java": """import java.util.*;
class Solution {
    static List<Integer> spiralOrder(int[][] matrix) {
        List<Integer> result = new ArrayList<>();
        int top = 0, bottom = matrix.length - 1, left = 0, right = matrix[0].length - 1;
        while (top <= bottom && left <= right) {
            for (int c = left; c <= right; c++) result.add(matrix[top][c]); top++;
            for (int r = top; r <= bottom; r++) result.add(matrix[r][right]); right--;
            if (top <= bottom) { for (int c = right; c >= left; c--) result.add(matrix[bottom][c]); bottom--; }
            if (left <= right) { for (int r = bottom; r >= top; r--) result.add(matrix[r][left]); left++; }
        }
        return result;
    }
}""",
            "cpp": """#include <vector>
using namespace std;
vector<int> spiralOrder(const vector<vector<int>>& matrix) {
    vector<int> result;
    int top = 0, bottom = matrix.size()-1, left = 0, right = matrix[0].size()-1;
    while (top <= bottom && left <= right) {
        for (int c = left; c <= right; ++c) result.push_back(matrix[top][c]); ++top;
        for (int r = top; r <= bottom; ++r) result.push_back(matrix[r][right]); --right;
        if (top <= bottom) { for (int c = right; c >= left; --c) result.push_back(matrix[bottom][c]); --bottom; }
        if (left <= right) { for (int r = bottom; r >= top; --r) result.push_back(matrix[r][left]); ++left; }
    }
    return result;
}""",
            "javascript": """function spiralOrder(matrix) {
  const result = [];
  let top = 0, bottom = matrix.length - 1, left = 0, right = matrix[0].length - 1;
  while (top <= bottom && left <= right) {
    for (let c = left; c <= right; c += 1) result.push(matrix[top][c]); top += 1;
    for (let r = top; r <= bottom; r += 1) result.push(matrix[r][right]); right -= 1;
    if (top <= bottom) { for (let c = right; c >= left; c -= 1) result.push(matrix[bottom][c]); bottom -= 1; }
    if (left <= right) { for (let r = bottom; r >= top; r -= 1) result.push(matrix[r][left]); left += 1; }
  }
  return result;
}""",
        },
        "lru": {
            "python": """from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity): self.capacity, self.data = capacity, OrderedDict()
    def get(self, key):
        if key not in self.data: return -1
        self.data.move_to_end(key); return self.data[key]
    def put(self, key, value):
        self.data[key] = value; self.data.move_to_end(key)
        if len(self.data) > self.capacity: self.data.popitem(last=False)""",
            "java": """import java.util.*;
class LRUCache extends LinkedHashMap<Integer, Integer> {
    private final int capacity;
    LRUCache(int capacity) { super(capacity, 0.75f, true); this.capacity = capacity; }
    int getValue(int key) { return getOrDefault(key, -1); }
    void putValue(int key, int value) { put(key, value); }
    protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) { return size() > capacity; }
}""",
            "cpp": """#include <list>
#include <unordered_map>
using namespace std;
class LRUCache {
    int capacity; list<pair<int,int>> order;
    unordered_map<int, list<pair<int,int>>::iterator> items;
public:
    explicit LRUCache(int capacity): capacity(capacity) {}
    int get(int key) { if (!items.count(key)) return -1; order.splice(order.begin(), order, items[key]); return items[key]->second; }
    void put(int key, int value) { if (items.count(key)) order.erase(items[key]); order.push_front({key,value}); items[key]=order.begin(); if ((int)items.size()>capacity) { items.erase(order.back().first); order.pop_back(); } }
};""",
            "javascript": """class LRUCache {
  constructor(capacity) { this.capacity = capacity; this.data = new Map(); }
  get(key) { if (!this.data.has(key)) return -1; const value = this.data.get(key); this.data.delete(key); this.data.set(key, value); return value; }
  put(key, value) { if (this.data.has(key)) this.data.delete(key); this.data.set(key, value); if (this.data.size > this.capacity) this.data.delete(this.data.keys().next().value); }
}""",
        },
    }


FAMILIES = [
    {
        "key": "two_sum", "title": "Complement Pair Lookup", "category": "Arrays / Hashing",
        "problem": "Given integer values and a target, return the indices of two distinct values whose sum equals the target. Return an empty list when no pair exists.",
        "input": "An integer array values and an integer target.", "output": "Two zero-based indices, or an empty list.",
        "constraints": ["2 <= values.length <= 10000", "Exactly one pair may be assumed only when stated", "Values may be negative or duplicated"],
        "example_in": "values = [2, 7, 11, 15], target = 9", "example_out": "[0, 1]",
        "example_why": "The values at indices 0 and 1 add to 9.",
        "hint": "Store information about values already visited so each complement can be checked immediately.",
        "brute": "Compare every unordered pair until a match is found. This uses O(n^2) time and O(1) extra space.",
        "optimized": "Scan once with a hash map from value to its earlier index. For each value, look up target minus value before inserting it.",
        "time": "O(n)", "space": "O(n)",
        "contexts": ["Payment Reconciliation", "Inventory Bundle", "Delivery Capacity", "Sensor Calibration", "Budget Allocation", "Order Discount", "Resource Pairing", "Ticket Pricing", "Portfolio Balance", "Warehouse Packing"],
    },
    {
        "key": "longest_unique", "title": "Longest Unique Sequence", "category": "Strings / Sliding Window",
        "problem": "Return the length of the longest contiguous substring that contains no repeated character.",
        "input": "A string text.", "output": "The maximum valid substring length.",
        "constraints": ["0 <= text.length <= 100000", "Treat characters as case-sensitive", "The substring must be contiguous"],
        "example_in": "text = 'abcabcbb'", "example_out": "3", "example_why": "The substring 'abc' has three distinct characters.",
        "hint": "Track the most recent index of each character and move only the left boundary forward.",
        "brute": "Start at every character and extend while maintaining a set. This can require O(n^2) time.",
        "optimized": "Use a sliding window and a last-seen map so each character enters the window once and the left boundary never moves backward.",
        "time": "O(n)", "space": "O(k), where k is the character set",
        "contexts": ["Session Token Audit", "Log Signature Scan", "Search Query Segment", "Device Identifier Check", "Message Stream Window", "DNA Symbol Run", "Keyboard Input Analysis", "URL Fragment Scan", "Document Character Run", "Telemetry Label Scan"],
    },
    {
        "key": "reverse_list", "title": "Reverse Linked Records", "category": "Linked Lists",
        "problem": "Reverse a singly linked list in place and return the new head without creating replacement nodes.",
        "input": "The head node of a singly linked list.", "output": "The head node of the reversed list.",
        "constraints": ["0 <= node count <= 100000", "Node values may repeat", "Reuse the existing nodes"],
        "example_in": "1 -> 2 -> 3 -> null", "example_out": "3 -> 2 -> 1 -> null", "example_why": "Every next pointer is redirected exactly once.",
        "hint": "Preserve the next node before changing the current node's pointer.",
        "brute": "Copy values to an array and rebuild or rewrite the list. This needs O(n) additional space.",
        "optimized": "Maintain previous, current, and following pointers and reverse one edge during each iteration.",
        "time": "O(n)", "space": "O(1)",
        "contexts": ["Undo History Chain", "Shipment Route Chain", "Revision Timeline", "Dependency Link Chain", "Playlist Navigation", "Audit Record Chain", "Task Sequence", "Browser History Nodes", "Transaction Ledger Chain", "Notification Chain"],
    },
    {
        "key": "valid_brackets", "title": "Nested Delimiter Validator", "category": "Stacks",
        "problem": "Determine whether every opening delimiter in a string is closed by the correct type in the correct order.",
        "input": "A string containing parentheses, square brackets, curly braces, and optional other characters.", "output": "true when the delimiters are balanced; otherwise false.",
        "constraints": ["0 <= text.length <= 100000", "Nested delimiters must close in LIFO order", "Non-delimiter characters may be ignored"],
        "example_in": "text = '{[()]}'", "example_out": "true", "example_why": "Every closer matches the most recent unmatched opener.",
        "hint": "The next closing symbol must match the most recently opened symbol.",
        "brute": "Repeatedly remove matching pairs until the string stops changing, which may take O(n^2) time.",
        "optimized": "Push opening delimiters on a stack and validate each closing delimiter against the stack top.",
        "time": "O(n)", "space": "O(n)",
        "contexts": ["Template Parser", "Configuration Validator", "Expression Checker", "Markup Scanner", "Query Syntax Guard", "Formula Validator", "Code Editor Check", "Message Format Guard", "Rule Engine Parser", "Command Grammar Check"],
    },
    {
        "key": "window_max", "title": "Rolling Window Maximum", "category": "Queues / Monotonic Queue",
        "problem": "For every contiguous window of a fixed size, return its maximum value.",
        "input": "An integer array values and a positive window size k.", "output": "An array containing one maximum per complete window.",
        "constraints": ["1 <= k <= values.length <= 100000", "Values may be negative", "Preserve window order"],
        "example_in": "values = [1,3,-1,-3,5,3,6,7], k = 3", "example_out": "[3,3,5,5,6,7]", "example_why": "Each result is the greatest value in its three-item window.",
        "hint": "Keep only indices that could still become the maximum of a future window.",
        "brute": "Scan all k values for every window, requiring O(nk) time.",
        "optimized": "Maintain a decreasing deque of candidate indices and remove expired indices from the front.",
        "time": "O(n)", "space": "O(k)",
        "contexts": ["Traffic Peak Monitor", "Server Load Peak", "Sales Window Peak", "Sensor Spike Tracker", "Queue Depth Peak", "Price Window High", "Demand Forecast Peak", "Latency Window Peak", "Energy Usage Peak", "Warehouse Throughput Peak"],
    },
    {
        "key": "group_anagrams", "title": "Canonical String Grouping", "category": "Hashing / Strings",
        "problem": "Group strings that contain exactly the same characters with the same multiplicities, regardless of order.",
        "input": "An array of lowercase strings.", "output": "A collection of anagram groups.",
        "constraints": ["0 <= word count <= 10000", "0 <= word length <= 100", "Every input word appears in exactly one group"],
        "example_in": "['eat','tea','tan','ate','nat','bat']", "example_out": "[['eat','tea','ate'],['tan','nat'],['bat']]", "example_why": "Words with the same sorted-character signature share a group.",
        "hint": "Create a canonical key that is identical for all rearrangements of a word.",
        "brute": "Compare character counts for every pair of words, which can approach O(w^2 * m).",
        "optimized": "Map each sorted-character signature to the list of words with that signature.",
        "time": "O(w * m log m)", "space": "O(w * m)",
        "contexts": ["Search Term Clustering", "Product Code Grouping", "Message Signature Grouping", "Dictionary Organizer", "Alias Detector", "Tag Normalization", "Puzzle Word Grouping", "Document Token Grouping", "Catalog Label Grouping", "Command Token Grouping"],
    },
    {
        "key": "level_order", "title": "Hierarchical Level Traversal", "category": "Trees / Breadth-First Search",
        "problem": "Return the values of a binary tree grouped by depth from the root.",
        "input": "The root of a binary tree.", "output": "A list of levels, each containing values from left to right.",
        "constraints": ["0 <= node count <= 100000", "Node values may repeat", "Preserve left-to-right order within a level"],
        "example_in": "tree = [3,9,20,null,null,15,7]", "example_out": "[[3],[9,20],[15,7]]", "example_why": "Breadth-first processing collects all nodes at one depth together.",
        "hint": "At each iteration, process exactly the number of nodes currently in the queue.",
        "brute": "Compute each node depth separately and append to that level, repeating path work.",
        "optimized": "Use a queue and snapshot its size before processing each complete level.",
        "time": "O(n)", "space": "O(w), where w is maximum tree width",
        "contexts": ["Organization Hierarchy", "Category Tree", "Permission Tree", "Decision Tree", "Comment Thread Tree", "File Index Tree", "Component Tree", "Menu Hierarchy", "Referral Tree", "Build Dependency Tree"],
    },
    {
        "key": "valid_bst", "title": "Ordered Tree Validation", "category": "Binary Search Trees",
        "problem": "Determine whether a binary tree satisfies the strict binary-search-tree ordering rule at every node.",
        "input": "The root of a binary tree.", "output": "true for a valid BST; otherwise false.",
        "constraints": ["0 <= node count <= 100000", "All comparisons are strict", "A descendant must respect every ancestor bound"],
        "example_in": "tree = [2,1,3]", "example_out": "true", "example_why": "Every left value is smaller and every right value is larger than its allowed ancestors.",
        "hint": "A parent-only comparison is insufficient; carry the valid numeric range into recursion.",
        "brute": "For every node, scan its entire left and right subtrees to verify extrema, taking O(n^2) in a skewed tree.",
        "optimized": "Pass exclusive lower and upper bounds down the tree and reject a value outside its permitted range.",
        "time": "O(n)", "space": "O(h)",
        "contexts": ["Price Index Validation", "Ranking Tree Audit", "Timestamp Tree Check", "Inventory Index Audit", "Score Tree Validation", "Routing Index Check", "Customer Index Audit", "Event Tree Validation", "Asset Index Check", "Priority Tree Audit"],
    },
    {
        "key": "components", "title": "Disconnected Group Counter", "category": "Graphs",
        "problem": "Count the number of connected components in an undirected graph represented by adjacency lists.",
        "input": "A map from every vertex to its neighboring vertices.", "output": "The number of disconnected connected groups.",
        "constraints": ["0 <= V <= 100000", "0 <= E <= 200000", "Every isolated vertex appears in the graph map"],
        "example_in": "edges = [(1,2),(2,3),(4,5)] with vertices 1..5", "example_out": "2", "example_why": "Vertices {1,2,3} and {4,5} form separate components.",
        "hint": "Every traversal started from an unvisited vertex discovers exactly one component.",
        "brute": "Check reachability separately for every pair of vertices, repeating most graph work.",
        "optimized": "Run DFS or BFS from each unvisited vertex and mark the entire discovered component.",
        "time": "O(V + E)", "space": "O(V)",
        "contexts": ["Social Cluster Counter", "Network Island Audit", "Service Dependency Groups", "Warehouse Route Groups", "Device Network Groups", "Account Relationship Clusters", "Delivery Region Groups", "Team Collaboration Clusters", "Document Link Groups", "Power Grid Islands"],
    },
    {
        "key": "merge_intervals", "title": "Overlapping Range Consolidation", "category": "Sorting / Intervals",
        "problem": "Merge all overlapping closed intervals and return a non-overlapping list sorted by start value.",
        "input": "A list of [start, end] intervals.", "output": "The merged non-overlapping intervals.",
        "constraints": ["0 <= interval count <= 100000", "start <= end", "Touching closed intervals may be merged"],
        "example_in": "[[1,3],[2,6],[8,10],[9,12]]", "example_out": "[[1,6],[8,12]]", "example_why": "The first two and last two ranges overlap.",
        "hint": "After sorting by start, only the most recently merged interval can overlap the next one.",
        "brute": "Repeatedly search all pairs for overlaps and restart after each merge, which can be quadratic.",
        "optimized": "Sort once by start and extend the last output interval whenever the next start is within its end.",
        "time": "O(n log n)", "space": "O(n)",
        "contexts": ["Meeting Calendar Merge", "Maintenance Window Merge", "Booking Range Merge", "Promotion Period Merge", "Downtime Range Merge", "Delivery Slot Merge", "Access Window Merge", "Video Segment Merge", "Subscription Period Merge", "Coverage Range Merge"],
    },
    {
        "key": "binary_search", "title": "Sorted Index Lookup", "category": "Searching / Binary Search",
        "problem": "Return the index of a target in a sorted integer array, or -1 when the target is absent.",
        "input": "A nondecreasing integer array and a target value.", "output": "The zero-based target index or -1.",
        "constraints": ["0 <= values.length <= 1000000", "Input is sorted", "Use logarithmic search"],
        "example_in": "values = [1,3,5,7,9], target = 7", "example_out": "3", "example_why": "The value 7 is stored at zero-based index 3.",
        "hint": "Compare with the middle value and discard the half that cannot contain the target.",
        "brute": "Scan values from left to right, requiring O(n) time.",
        "optimized": "Maintain an inclusive search range and halve it after every comparison.",
        "time": "O(log n)", "space": "O(1)",
        "contexts": ["Product ID Lookup", "Timestamp Search", "Price Point Lookup", "Version Number Search", "Sensor Threshold Lookup", "Employee ID Search", "Order Sequence Lookup", "Rank Search", "Inventory Code Search", "Checkpoint Lookup"],
    },
    {
        "key": "subsets", "title": "Power Set Generator", "category": "Recursion / Backtracking",
        "problem": "Generate every subset of a list of distinct values, including the empty set and the full set.",
        "input": "An array of n distinct integers.", "output": "All 2^n subsets in any order.",
        "constraints": ["0 <= n <= 20", "Input values are distinct", "Every subset must appear exactly once"],
        "example_in": "values = [1,2,3]", "example_out": "[[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]", "example_why": "Each value is independently included or excluded.",
        "hint": "For each value, duplicate the subsets already built and append the value to each copy.",
        "brute": "Enumerate every bit mask and inspect all n positions, which uses O(n * 2^n) work.",
        "optimized": "Grow the result iteratively by cloning existing subsets with the current value appended.",
        "time": "O(n * 2^n)", "space": "O(n * 2^n) for output",
        "contexts": ["Feature Combination Builder", "Permission Set Generator", "Bundle Combination Generator", "Test Flag Combination", "Ingredient Combination", "Configuration Combination", "Filter Combination", "Team Selection Options", "Alert Rule Combination", "Capability Set Builder"],
    },
    {
        "key": "coin_change", "title": "Minimum Denomination Count", "category": "Dynamic Programming",
        "problem": "Return the minimum number of available denominations needed to form an exact target amount, or -1 if impossible.",
        "input": "Positive integer denominations and a nonnegative target.", "output": "Minimum item count or -1.",
        "constraints": ["1 <= denomination count <= 100", "0 <= target <= 10000", "Each denomination may be reused"],
        "example_in": "denominations = [1,2,5], target = 11", "example_out": "3", "example_why": "5 + 5 + 1 uses three items and no two-item solution exists.",
        "hint": "Let each smaller amount remember the fewest items needed to construct it.",
        "brute": "Try every sequence of denominations recursively, causing exponential repeated work.",
        "optimized": "Use bottom-up dynamic programming where dp[x] is one plus the best reachable dp[x - denomination].",
        "time": "O(target * denominations)", "space": "O(target)",
        "contexts": ["Cash Change Planner", "Token Pack Optimizer", "Resource Unit Planner", "Stamp Count Optimizer", "Credit Bundle Planner", "Capacity Block Planner", "Voucher Combination", "Package Size Optimizer", "Battery Unit Planner", "Point Redemption Planner"],
    },
    {
        "key": "activity_selection", "title": "Maximum Compatible Schedule", "category": "Greedy Algorithms",
        "problem": "Select the largest possible set of non-overlapping half-open intervals.",
        "input": "A list of [start, end] intervals.", "output": "One maximum-size compatible interval set.",
        "constraints": ["0 <= interval count <= 100000", "start < end", "An interval may begin when the previous one ends"],
        "example_in": "[[1,3],[2,5],[4,7],[6,9],[8,10]]", "example_out": "[[1,3],[4,7],[8,10]]", "example_why": "Choosing the earliest finishing compatible interval leaves maximum room for later choices.",
        "hint": "A locally chosen interval should leave as much remaining time as possible.",
        "brute": "Enumerate interval subsets and test compatibility, requiring exponential time.",
        "optimized": "Sort by finish time and repeatedly select the next interval whose start is not before the last finish.",
        "time": "O(n log n)", "space": "O(n) for the selected output",
        "contexts": ["Interview Room Schedule", "Machine Job Schedule", "Delivery Slot Schedule", "Classroom Booking", "Ad Campaign Schedule", "Maintenance Task Schedule", "Consultation Schedule", "Recording Studio Schedule", "Charging Station Schedule", "Meeting Selection"],
    },
    {
        "key": "window_sum", "title": "Maximum Fixed-Window Total", "category": "Sliding Window",
        "problem": "Return the maximum sum among all contiguous windows of exactly k values.",
        "input": "An integer array values and an integer window size k.", "output": "The greatest complete-window sum.",
        "constraints": ["1 <= k <= values.length <= 100000", "Values may be negative", "Use exactly k consecutive values"],
        "example_in": "values = [2,1,5,1,3,2], k = 3", "example_out": "9", "example_why": "The window [5,1,3] has the greatest sum.",
        "hint": "Adjacent windows differ by only one outgoing and one incoming value.",
        "brute": "Sum all k values independently for every start, requiring O(nk) time.",
        "optimized": "Compute the first window once, then update the sum by subtracting the outgoing value and adding the incoming value.",
        "time": "O(n)", "space": "O(1)",
        "contexts": ["Peak Weekly Sales", "Maximum Traffic Block", "Best Revenue Window", "Highest Energy Window", "Peak Request Window", "Best Study Streak", "Maximum Output Period", "Peak Footfall Window", "Highest Demand Block", "Best Conversion Window"],
    },
    {
        "key": "sorted_pair", "title": "Sorted Two-Pointer Match", "category": "Two Pointer",
        "problem": "In a sorted array, return two indices whose values sum to a target, or an empty list if none exist.",
        "input": "A sorted integer array and a target.", "output": "Two zero-based indices or an empty list.",
        "constraints": ["2 <= values.length <= 100000", "Input is nondecreasing", "Use constant auxiliary space"],
        "example_in": "values = [1,2,4,6,10], target = 8", "example_out": "[1,3]", "example_why": "Values 2 and 6 sum to 8.",
        "hint": "Use the sorted order to decide which pointer must move after each comparison.",
        "brute": "Compare every pair, requiring O(n^2) time.",
        "optimized": "Start at both ends; increase the left pointer for a low sum and decrease the right pointer for a high sum.",
        "time": "O(n)", "space": "O(1)",
        "contexts": ["Sorted Price Pair", "Capacity Pair Match", "Score Pair Search", "Sorted Weight Pair", "Distance Pair Match", "Sorted Credit Pair", "Rank Pair Lookup", "Sorted Duration Pair", "Inventory Pair Search", "Budget Pair Match"],
    },
    {
        "key": "kth_largest", "title": "Kth Highest Value", "category": "Heap / Priority Queue",
        "problem": "Return the kth largest value in an unsorted array without requiring all values to remain ordered.",
        "input": "An integer array values and integer k.", "output": "The kth largest value.",
        "constraints": ["1 <= k <= values.length <= 100000", "Values may repeat", "Duplicate values occupy separate ranks"],
        "example_in": "values = [3,2,1,5,6,4], k = 2", "example_out": "5", "example_why": "After descending order, 5 is in the second position.",
        "hint": "Keep only the k best candidates seen so far and make the weakest candidate easy to remove.",
        "brute": "Sort all values and index the result, requiring O(n log n) time.",
        "optimized": "Maintain a min-heap of size k; after the scan, its root is the kth largest value.",
        "time": "O(n log k)", "space": "O(k)",
        "contexts": ["Leaderboard Rank", "Top Sensor Reading", "Kth Highest Sale", "Priority Rank Lookup", "Kth Largest Order", "Exam Score Rank", "Latency Rank", "Bid Rank Lookup", "Inventory Rank", "Performance Rank"],
    },
    {
        "key": "single_number", "title": "Unpaired Identifier", "category": "Bit Manipulation",
        "problem": "Every integer appears exactly twice except one. Return the value that appears once using constant extra space.",
        "input": "A nonempty integer array.", "output": "The unique unpaired integer.",
        "constraints": ["1 <= values.length <= 100000", "Exactly one value appears once", "Every other value appears twice"],
        "example_in": "values = [4,1,2,1,2]", "example_out": "4", "example_why": "Equal values cancel under XOR, leaving only 4.",
        "hint": "A value XOR itself becomes zero, and zero XOR x becomes x.",
        "brute": "Count values in a hash map, taking O(n) additional space.",
        "optimized": "XOR every value; paired values cancel regardless of order.",
        "time": "O(n)", "space": "O(1)",
        "contexts": ["Unpaired Device ID", "Missing Scan Partner", "Unique Transaction ID", "Unpaired Badge Code", "Unique Packet Number", "Unpaired Ticket ID", "Unique Sensor Code", "Unmatched Order Code", "Unique Asset ID", "Unpaired Event Code"],
    },
    {
        "key": "spiral", "title": "Spiral Matrix Traversal", "category": "Matrix Problems",
        "problem": "Return every matrix value in clockwise spiral order, starting at the top-left corner.",
        "input": "A nonempty rectangular matrix.", "output": "A flat list in clockwise spiral order.",
        "constraints": ["1 <= rows, columns <= 500", "The matrix may be rectangular", "Visit each cell exactly once"],
        "example_in": "[[1,2,3],[4,5,6],[7,8,9]]", "example_out": "[1,2,3,6,9,8,7,4,5]", "example_why": "The traversal consumes the outer boundary before the center.",
        "hint": "Maintain top, bottom, left, and right boundaries and shrink them after each side.",
        "brute": "Simulate movement with a visited matrix, using O(rows * columns) extra space.",
        "optimized": "Traverse four current boundaries and shrink them while checking whether rows or columns remain.",
        "time": "O(rows * columns)", "space": "O(1) excluding output",
        "contexts": ["Image Pixel Spiral", "Warehouse Grid Scan", "Seat Map Spiral", "Heatmap Traversal", "Game Board Spiral", "Spreadsheet Spiral Export", "Sensor Grid Scan", "Display Panel Traversal", "Farm Plot Spiral", "Document Tile Traversal"],
    },
    {
        "key": "lru", "title": "Least-Recently-Used Cache", "category": "Practical Real-World Programming",
        "problem": "Implement a fixed-capacity cache with O(1) get and put operations that evicts the least recently used key when full.",
        "input": "A capacity followed by get(key) and put(key, value) operations.", "output": "get returns the value or -1; put updates cache state.",
        "constraints": ["1 <= capacity <= 10000", "Keys and values are integers", "Both operations must be O(1) average time"],
        "example_in": "capacity=2; put(1,1); put(2,2); get(1); put(3,3); get(2)", "example_out": "1, -1", "example_why": "Reading key 1 makes key 2 least recent, so inserting key 3 evicts key 2.",
        "hint": "Combine constant-time key lookup with a structure that can move and evict nodes in constant time.",
        "brute": "Store timestamps and scan all keys on eviction, making put O(capacity).",
        "optimized": "Combine a hash map with recency ordering via a doubly linked list or an access-ordered map.",
        "time": "O(1) average per operation", "space": "O(capacity)",
        "contexts": ["API Response Cache", "Profile Data Cache", "Search Result Cache", "Image Metadata Cache", "Feature Flag Cache", "Route Lookup Cache", "Session Data Cache", "Product Detail Cache", "Model Output Cache", "Configuration Cache"],
    },
]


def build_practical_coding_questions():
    """Build exactly 200 unique practical coding learning records."""
    solutions = _solution_library()
    required_languages = {"python", "java", "cpp", "javascript"}
    if len(FAMILIES) != 20 or any(len(family["contexts"]) != 10 for family in FAMILIES):
        raise RuntimeError("Practical coding source must contain 20 families with 10 contexts each.")
    if any(set(solutions.get(family["key"], {})) != required_languages for family in FAMILIES):
        raise RuntimeError("Every practical coding family must provide all four solution languages.")
    records = []
    for family in FAMILIES:
        for context in family["contexts"]:
            number = len(records) + 1
            difficulty = "Easy" if number <= 70 else "Medium" if number <= 160 else "Hard"
            title = f"{context}: {family['title']}"
            company = PRACTICAL_COMPANIES[(number - 1) % len(PRACTICAL_COMPANIES)]
            question = f"{title}. {family['problem']}"
            optimized = family["optimized"]
            records.append(
                {
                    "id": f"PC{number:03d}",
                    "question_type": "coding",
                    "category": "Practical Coding",
                    "subcategory": family["category"],
                    "company": company,
                    "difficulty": difficulty,
                    "question": question,
                    "answer": f"Use the optimized {family['title'].lower()} strategy and verify the supplied edge cases before submitting.",
                    "detailed_explanation": (
                        f"{optimized} The reference implementation preserves the core invariant at every step. "
                        f"Its claimed complexity is {family['time']} time and {family['space']} space."
                    ),
                    "example": f"Input: {family['example_in']}\nOutput: {family['example_out']}\nWhy: {family['example_why']}",
                    "tags_json": safe_json_dumps([family["category"], context, "Practical Coding", company]),
                    "topic": family["category"],
                    "estimated_study_time": 12 if difficulty == "Easy" else 18 if difficulty == "Medium" else 25,
                    "frequency": ["Very Common", "Common", "Moderate", "Rare"][(number - 1) % 4],
                    "related_questions_json": "[]",
                    "approach": f"Brute force: {family['brute']} Optimized: {optimized}",
                    "code": solutions[family["key"]]["python"],
                    "time_complexity": family["time"],
                    "space_complexity": family["space"],
                    "common_mistakes": "Ignoring an empty or minimal input, mutating caller-owned data unexpectedly, missing duplicate values, or claiming complexity without deriving it.",
                    "interview_tip": "Clarify the input contract, describe the baseline, state the optimized invariant, then test one normal and one boundary case before coding.",
                    "title": title,
                    "problem": family["problem"],
                    "input_format": family["input"],
                    "output_format": family["output"],
                    "constraints_json": safe_json_dumps(family["constraints"]),
                    "example_input": family["example_in"],
                    "example_output": family["example_out"],
                    "example_explanation": family["example_why"],
                    "hints_json": safe_json_dumps([family["hint"]]),
                    "brute_force_approach": family["brute"],
                    "optimized_approach": optimized,
                    "solutions_json": safe_json_dumps(solutions[family["key"]]),
                    "complexity_explanation": (
                        f"The algorithm runs in {family['time']} because it processes the required state without redundant full rescans. "
                        f"It uses {family['space']} to retain only the auxiliary state required by the optimized strategy."
                    ),
                }
            )

    if len(records) != 200:
        raise RuntimeError(f"Practical coding catalog must contain 200 questions, found {len(records)}.")
    if len({record["id"] for record in records}) != 200 or len({record["question"] for record in records}) != 200:
        raise RuntimeError("Practical coding IDs and question text must be unique.")
    expected_difficulty = {"Easy": 70, "Medium": 90, "Hard": 40}
    actual_difficulty = {level: sum(record["difficulty"] == level for record in records) for level in expected_difficulty}
    if actual_difficulty != expected_difficulty:
        raise RuntimeError(f"Unexpected practical coding difficulty distribution: {actual_difficulty}.")
    return records
