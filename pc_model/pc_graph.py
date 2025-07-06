"""
Graph implementation that 

"""
import copy

_CURR_ID = 0
def _GET_UID():
        """
        Increments and returns an ID that is associated with a node
        """
        global _CURR_ID
        _CURR_ID += 1
        return _CURR_ID


class BaseNode():
    def __init__(self, data = None, parents = None, children = None):
        self.data      = data
        self._parents  = parents  if parents  is not None else []
        self._children = children if children is not None else []
        self._id = _GET_UID()

    def get_id(self):
        return self._id
    
    def get_children(self):
        return tuple(self._children)

    def add_child(self, child: "Node"):
        duplicate = child not in self._children
        if not duplicate:
            self._children.append(child)
        return duplicate

    def remove_child(self, child: "Node"):
        try:
            self._children.remove(child)
            return True
        except ValueError:
            return False
    
    def get_parents(self):
        return tuple(self._parents)

    def add_parent(self, parent: "Node"):
        duplicate = parent in self._parents
        if not duplicate:
            self._parents.append(parent)
        return duplicate

    def remove_parent(self, parent: "Node"):
        try:
            self._children.remove(parent)
            return True
        except ValueError:
            return False
        
    def __deepcopy__(self, memo):
        return type(self)(data=self.data, parents=self._parents.copy(), children=self._children.copy())

    def __str__(self):
        return f"<{type(self).__name__}: data({type(self.data).__name__})={self.data} children={tuple(self._children)} parents={tuple(self._parents)}>"
        
    def __repr__(self):
        return f"<{type(self).__name__}: data({type(self.data).__name__})={self.data}>"


class Graph():
    def __init__(self):
        self._nodes : list[BaseNode] = []
    
    def add_node(self, data):
        if type(data) is BaseNode:
            self._nodes.append(data)
        else:
            self._nodes.append(BaseNode(data=data))
        return self._nodes[-1]
    
    def add_edge(self, n1: BaseNode, n2: BaseNode):
        if n1 not in self._nodes:
            self._nodes.append(n1)
        if n2 not in self._nodes:
            self._nodes.append(n2)
        n1.add_child(n2) 
        n2.add_parent(n1)

    def remove_edge(self, n1: BaseNode, n2: BaseNode):
        n1.remove_child(n2)
        n2.remove_parent(n1)
    
    def remove_node(self, n: BaseNode):
        if n in self._nodes:
            self._nodes.remove(n)
            for x in self._nodes:
                x.remove_child(n)

    def clone_node(self, n: BaseNode, copies=1):
        """
        Clone the specified node copies times. Makes deepcopies of children and 
        parents of original node. Useful to make multiple consumers that split
        load from a number of producers.
        Notes:
         - Current behavior only supports cloning a node with a single parent and single child 
        """
        for _ in range(copies):
            self._nodes.append(copy.deepcopy(n))

    def add_linear_chain(self, objs):
        """
        Creates a linked list of nodes with each node containing an element from objs.
        Nodes are linked together in order they appear in objs with objs[0] not
        having a parent, and objs[-1] not having a child
        """
        nodes = [self.add_node(obj) for obj in objs]
        lastNode, *rest = nodes            
        for n in rest:
            self.add_edge(lastNode, n)
            lastNode = n
        return nodes


    def __iter__(self):
        return iter(tuple(self._nodes))
    
    def print_graph(self):
        for x in self._nodes:
            print(x)

    def is_empty(self):
        return len(self._nodes) == 0

def __testing():
    """
    Random testing stuff
    """
    n1 = BaseNode("1")
    n2 = BaseNode("2")
    n3 = BaseNode("3")
    n4 = BaseNode("4")

    g = Graph()

    g.add_edge(n1, n1)
    g.add_edge(n1, n2)
    g.add_edge(n1, n3)
    g.add_edge(n1, n4)
    g.print_graph()

    print("=================================================================================================")

    g.remove_edge(n1, n2)
    g.print_graph()

    print("=================================================================================================")

    g.remove_node(n3)
    g.print_graph()


if __name__ == "__main__":
    __testing()