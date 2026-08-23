from src.mascot import _biblePath, loadBibleSnippet, mascotForStandard

print("zunda", mascotForStandard("zunda"), _biblePath("zundamon"))
print(loadBibleSnippet("zundamon")[:120])
print("anko", mascotForStandard("anko"), _biblePath("ankomon"))
print("azuki", mascotForStandard("azuki"), _biblePath("ankomon"))
print(loadBibleSnippet("ankomon")[:120])
