# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2015, Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
import numpy as np

from .widget import Widget
from ...visuals import AxisVisual


class AxisWidget(Widget):
    def __init__(self, orientation='left', **kwargs):
        if 'tick_direction' not in kwargs:
            tickdir = {'left': (-1, 0), 'right': (1, 0), 'bottom': (0, 1), 
                       'top': (0, -1)}[orientation]
            kwargs['tick_direction'] = tickdir
        self.axis = AxisVisual(**kwargs)
        self.orientation = orientation
        Widget.__init__(self)
        self.add_subvisual(self.axis)
        self._linked_view = None
        
    def on_resize(self, event):
        self._update_axis()
        
    def _update_axis(self):
        self.axis.pos = self._axis_ends()
        
    def _axis_ends(self):
        r = self.inner_rect
        if self.orientation == 'left':
            return np.array([[r.right, r.bottom], [r.right, r.top]])
        elif self.orientation == 'bottom':
            return np.array([[r.left, r.bottom], [r.right, r.bottom]])
        
    def link_view(self, view):
        """Link this axis to a ViewBox such that its domain always matches the
        visible range in the ViewBox.
        """
        if view is self._linked_view:
            return
        if self._linked_view is not None:
            self._linked_view.scene.transform.changed.disconnect(
                self._view_changed)
        self._linked_view = view
        view.scene.transform.changed.connect(self._view_changed)
        self._view_changed()
        
    def _view_changed(self, event=None):
        """Linked view transform has changed; update ticks.
        """
        tr = self.node_transform(self._linked_view.scene)
        p1, p2 = tr.map(self._axis_ends())
        if self.orientation in ('left', 'right'):
            self.axis.domain = (p1[1], p2[1])
        else:
            self.axis.domain = (p1[0], p2[0])