## relation
Allen's interval algebra中的13种关系的缩写对应，自然语言模板可参考generate_hints.py中的`HINT_TEMPLATE`
1. p: precedes/before  
2. P: preceded_by/after  
3. m: meets  
4. M: met_by  
5. o: overlaps   
6. O: overlapped_by  
7. f: finishes
8. F: finished_by
9. s: starts
10. S: started_by
11. d: during
12. D: contains
13. e: equals

## attribute
Allen关系可以以下几种属性归类
1. start(happen) time: before/after/start(same)  
2. end time: before/after/end(same)  
3. overlap: yes/no  
4. duration: longer/shorter/no determine/equal  
5. meet(follow): yes/no  
## funcs
这些函数名可以为属性的每一种可能项提供相应的自然语言模板，具体函数在generate_hints.py中给出
overlaps,
no_determine_length,
happen_before,
happen_after,
ends_before,
ends_after,
no_overlap,
longer_than,
shorter_than,
starts,
ends,
no_meeting,
only_follow,
equals
## relation-attribute
Allen关系对应的能最快确认该关系所需的属性，括号内是冗余属性，只能辅助排除，但不能确定到唯一关系  
p(P): 1/2 3 5 (4) 
m(M): 1/2 5 (3 4)  
o(O): 1/2 3 (4 5)  
f(F): 1 2 (3 4 5)  
s(S): 1 2 (3 4 5)  
d(D): 1/2 4 (3)  
e: 4 (1 2 3 5)  