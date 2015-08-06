# -*- coding: utf-8 -*-
# Copyright (c) 2015, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
"""
Force-Directed Graph Layout
===========================

This module contains implementations for a force-directed layout, where each
edge is modelled like a spring, and the whole graph tries to reach a state
which requires the minimum energy.
"""

import numpy as np

from ..util import straight_line_vertices, rescale_layout


class fruchterman_reingold:
    """
    Fruchterman-Reingold implementation adapted from NetworkX.

    Paramters
    ---------
    optimal : number
        Optimal distance between nodes. Defaults to :math:`1/\sqrt{N}` where
        N is the number of nodes.
    iterations : int
        Number of iterations to perform for layout calculation.
    pos : array
        Initial positions of the nodes
    """

    def __init__(self, optimal=None, iterations=50, pos=None):
        self.dim = 2
        self.optimal = optimal
        self.iterations = iterations
        self.num_nodes = None
        self.pos = pos

    def __call__(self, adjacency_mat, directed=False):
        """
        Starts the calculation of the graph layout.

        This is a generator, and after each iteration it yields the new
        positions for the nodes, together with the vertices for the edges
        and the arrows.

        There are two solvers here: one specially adapted for SciPy sparse
        matrices, and the other for larger networks.

        Parameters
        ----------
        adjacency_mat : array
            The graph adjacency matrix.
        directed : bool
            Wether the graph is directed or not. If this is True,
            it will draw arrows for directed edges.

        Yields
        ------
        layout : tuple
            For each iteration of the layout calculation it yields a tuple
            containing (node_vertices, line_vertices, arrow_vertices). These
            vertices can be passed to the `MarkersVisual` and `ArrowVisual`.
        """
        if adjacency_mat.shape[0] != adjacency_mat.shape[1]:
            raise ValueError("Adjacency matrix should be square.")

        self.num_nodes = adjacency_mat.shape[0]

        if self.num_nodes < 500:
            # Use the sparse solver
            solver = self._sparse_fruchterman_reingold
        else:
            solver = self._fruchterman_reingold

        for result in solver(adjacency_mat, directed):
            yield result

    def _fruchterman_reingold(self, adjacency_mat, directed=False):
        if self.optimal is None:
            self.optimal = 1 / np.sqrt(self.num_nodes)

        if self.pos is None:
            # Random initial positions
            pos = np.asarray(
                np.random.random((self.num_nodes, self.dim)),
                dtype='f32'
            )
        else:
            pos = self.pos.astype('f32')

        # Yield initial positions
        line_vertices, arrows = straight_line_vertices(adjacency_mat, pos,
                                                       directed)
        yield pos, line_vertices, arrows

        # The initial "temperature"  is about .1 of domain area (=1x1)
        # this is the largest step allowed in the dynamics.
        t = 0.1

        # Simple cooling scheme.
        # Linearly step down by dt on each iteration so last iteration is
        # size dt.
        dt = t / float(self.iterations+1)
        delta = np.zeros(
            (pos.shape[0], pos.shape[0], pos.shape[1]),
            dtype=adjacency_mat.dtype
        )

        # The inscrutable (but fast) version
        # This is still O(V^2)
        # Could use multilevel methods to speed this up significantly
        for iteration in range(self.iterations):
            # Matrix of difference between points
            for i in range(pos.shape[1]):
                delta[:, :, i] = pos[:, i, None] - pos[:, i]

            # Distance between points
            distance = np.sqrt((delta**2).sum(axis=-1))
            # Enforce minimum distance of 0.01
            distance = np.where(distance < 0.01, 0.01, distance)
            # Displacement "force"
            displacement = np.transpose(
                np.transpose(delta) * (
                    self.optimal * self.optimal/distance**2 -
                    adjacency_mat*distance/self.optimal
                )
            ).sum(axis=1)

            # update positions
            length = np.sqrt((displacement**2).sum(axis=1))
            length = np.where(length < 0.01, 0.1, length)
            delta_pos = np.transpose(np.transpose(displacement)*t/length)
            pos += delta_pos
            pos = rescale_layout(pos)

            # cool temperature
            t -= dt

            # Calculate edge vertices and arrows
            line_vertices, arrows = straight_line_vertices(adjacency_mat,
                                                           pos, directed)

            yield pos, line_vertices, arrows

    def _sparse_fruchterman_reingold(self, adjacency_mat, directed=False):
        # Optimal distance between nodes
        if self.optimal is None:
            self.optimal = 1 / np.sqrt(self.num_nodes)

        # make sure we have a LIst of Lists representation
        adjacency_mat = adjacency_mat.tolil()

        if self.pos is None:
            # Random initial positions
            pos = np.asarray(
                np.random.random((self.num_nodes, self.dim)),
                dtype='f32'
            )
        else:
            pos = self.pos.astype('f32')

        # Yield initial positions
        line_vertices, arrows = straight_line_vertices(adjacency_mat, pos,
                                                       directed)
        yield pos, line_vertices, arrows

        # The initial "temperature"  is about .1 of domain area (=1x1)
        # This is the largest step allowed in the dynamics.
        t = 0.1
        # Simple cooling scheme.
        # Linearly step down by dt on each iteration so last iteration is
        # size dt.
        dt = t / float(self.iterations+1)

        displacement = np.zeros((self.dim, self.num_nodes))
        for iteration in range(self.iterations):
            displacement *= 0
            # Loop over rows
            for i in range(adjacency_mat.shape[0]):
                # difference between this row's node position and all others
                delta = (pos[i]-pos).T
                # distance between points
                distance = np.sqrt((delta**2).sum(axis=0))
                # enforce minimum distance of 0.01
                distance = np.where(distance < 0.01, 0.01, distance)
                # the adjacency matrix row
                row = np.asarray(adjacency_mat.getrowview(i).toarray())
                # displacement "force"
                displacement[:, i] += (
                    delta * (
                        self.optimal *
                        self.optimal/distance**2 -
                        row*distance/self.optimal
                    )
                ).sum(axis=1)

            # Update positions
            length = np.sqrt((displacement**2).sum(axis=0))
            length = np.where(length < 0.01, 0.1, length)
            pos += (displacement*t/length).T
            pos = rescale_layout(pos)

            # Cool temperature
            t -= dt

            # Calculate line vertices
            line_vertices, arrows = straight_line_vertices(adjacency_mat,
                                                           pos, directed)

            yield pos, line_vertices, arrows