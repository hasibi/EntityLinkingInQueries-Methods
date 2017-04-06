"""
Methods for graph based features, based on Wikipedia graph.

@author: Faegheh Hasibi
"""

from nordlys.erd import econfig
from igraph import Graph


class GraphFeat(object):
    """
    Attributes:
        entities: Dictionary {en_id: entity, ...}
        attributes: attributes of all entities in the form of a dictionary.
            (e.g. {'en_id':{'mention': 'm1','score': 1234}, ...})
    """

    def __init__(self, entities, attributes=None):
        self.entities = entities
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes
        self.graph = None

    def __gen_graph(self):
        """Generates a graph out of entities in the set. """
        if self.graph is not None:
            return self.graph

        g = Graph()
        # adds vertices
        i = 0
        for en_id in self.entities:
            g.add_vertices(1)
            g.vs[i]['name'] = en_id
            i += 1
        # adds attributes for vertices
        for en in self.attributes:
            v_id = g.vs.find(name=en).index
            for att_name, val in self.attributes[en].iteritems():
                g.vs[v_id][att_name] = val
        # adds edges
        for v in g.vs:
            entity_id = v['name']
            entity = self.entities[entity_id]
            entity_links = set(entity.get(econfig.WIKILINKS, []))
            for v2 in g.vs:
                # adds the edge if the entity is linked to the other entity and the edge has not added before.
                if (v.index != v2.index) and (v2['name'] in entity_links) and (not g.are_connected(v, v2)):
                    # print str(v.index) + ":" + v['name'] + "   " + str(v2.index) + ":" + v2['name']
                    g.add_edge(v.index, v2.index)
        self.graph = g
        return self.graph

    @property
    def num_nodes(self):
        """Number of nodes. """
        self.__gen_graph()
        return len(self.graph.vs)

    @property
    def num_edges(self):
        """Number of nodes. """
        self.__gen_graph()
        return len(self.graph.es)

    @property
    def vs(self):
        """Number of nodes. """
        self.__gen_graph()
        return self.graph.vs

    @property
    def es(self):
        """Number of edges. """
        self.__gen_graph()
        return self.graph.es

    def common_neighbors(self):
        """Size of common neighbors that all entities have."""
        if len(self.entities) < 1:
            raise Exception("Calculating common neighbors: No entity is given")
        if len(self.entities) == 1:
            return -1
        cmn_neighbors = set(self.entities.values()[0].get(econfig.WIKILINKS, []))
        for entity in self.entities.values():
            cmn_neighbors &= set(entity.get(econfig.WIKILINKS, []))
        return len(cmn_neighbors)

    def all_neighbors(self):
        """Size of all neighbors that all entities have."""
        if len(self.entities) < 1:
            raise Exception("Calculating all neighbors: No entity is given")
        all_neighbors = set()
        for entity in self.entities.values():
            all_neighbors |= set(entity.get(econfig.WIKILINKS, []))
        return len(all_neighbors)

    def completeness(self):
        """ num_edges / num_edges in complete graph """
        if self.num_nodes == 1:
            return 1.0
        n_complete = self.num_nodes * (self.num_nodes - 1) / 2
        return float(self.num_edges) / n_complete

    def jc(self):
        """
        Jaccard similarity w.r.t the number of links in dbpedia graph:
            #common_neighbors / #all_neighbors.
        """
        if len(self.entities) == 1:
            return -1
        if self.all_neighbors() == 0:
            return 0
        return float(self.common_neighbors()) / self.all_neighbors()

def main():
    # en0 = "<dbpedia:New_York>"
    # en1 = "<dbpedia:The_Beatles:_Rock_Band>"
    en12 = "<dbpedia:Roman_Catholic_Diocese_of_Las_Vegas>"
    en13 = "<dbpedia:Charlie_Sheen>"
    en14 = "<dbpedia:Lindsay_Lohan>"
    en_set = [en13, en14, en12]
    graph_ftrs = GraphFeat(en_set)

    print graph_ftrs.graph
    print "Number of nodes: " + str(graph_ftrs.num_nodes)
    print "Number of edges: " + str(graph_ftrs.num_edges)
    print "Number of common neighbors: " + str(graph_ftrs.common_neighbors())
    print "Number of all neighbors: " + str(graph_ftrs.all_neighbors())
    print "Connectedness: " + str(graph_ftrs.jc())
    print "Graph completeness: " + str(graph_ftrs.completeness())

if __name__ == '__main__':
    main()
