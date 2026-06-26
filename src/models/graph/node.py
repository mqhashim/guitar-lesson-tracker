"""
Spec:
Node: self
fields:
id: str | int
name: str
prerequisites: [Node]
done: bool
description: str | md
drills: [drill]
conclusion: str | md

methods:
get_parents
add parent/s
check_complete
get_description
render_description
get_conclusion
render_conclusion
get_drills

"""


class GraphNode:
    def __init__(self):
        pass

    def parents(self):
        pass
