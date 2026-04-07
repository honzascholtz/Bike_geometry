#!/usr/bin/env python3
"""
creator - Jan Scholtz
bike_geometry.py  –  Parse and plot bicycle frame geometry from a tab-separated file.

Coordinate system (origin = Bottom Bracket centre):
    +x  →  toward front wheel
    +y  ↑  upward
"""

from cgitb import text
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, FancyArrowPatch
import Graph_setup as gph
gph.graph_format_official()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
WHEEL_RADIUS = 336   # mm – 700c road wheel + ~25 mm tyre (622 mm rim ÷ 2 + tyre)
 
PALETTE = {
    'seat_tube' : '#E74C3C',
    'top_tube'  : '#2980B9',
    'down_tube' : '#27AE60',
    'head_tube' : '#E67E22',
    'chainstay' : '#8E44AD',
    'seat_stay' : '#16A085',
    'fork'      : '#D35400',
    'stem'      : '#C0392B',
    'spacer'    : '#5D6D7E',
    'bar'       : '#1A252F',
    'saddle'    : '#1A252F',
    'wheel_rim' : '#444444',
    'wheel_tyre': '#1a1a1a',
    'spoke'     : '#aaaaaa',
    'bb_shell'  : '#cccccc',
    'point'     : '#111111',
    'dim_blue'  : '#1A5276',
    'dim_red'   : '#922B21',
    'dim_orange': '#935116',
    'dim_grey'  : '#555555',
    'dim_green' : '#1D6A39',
    'ref_line'  : '#bbbbbb',
    'ground'    : '#CCCCCC',
    'bg'        : '#F7F7F7',
}

# ─────────────────────────────────────────────────────────────────────────────
# Use functions
# ─────────────────────────────────────────────────────────────────────────────
def plot_geometry(path: str):

    f, ax = plt.subplots(figsize=(10, 6))
    geo = Geometry(path)

    geo.plot_bike(f, ax)
    return f,ax


def plot_comparison(paths: list, colors=None, names=None):

    if names is None:
        names = [f"Bike {i+1}" for i in range(len(paths))]
    if colors is None:
        colors = ['blue', 'orange', 'green', 'purple', 'red', 'cyan', 'magenta', 'brown', 'olive', 'teal']
        colors = colors[:len(paths)]

    fig, ax = plt.subplots(figsize=(12, 6))
    order = np.array([], dtype=int)

    print(paths, names, colors)

    for i, (p, c, name) in enumerate(zip(paths, colors,names)):
        G = Geometry(p)
    
        fig = G.plot_comp(fig, ax, p, color=c)

        ax.plot([], [], color=c, label=name)
        
        order= np.append(order, -i-1)


    from matplotlib.legend_handler import HandlerTuple       
    h, l = ax.get_legend_handles_labels()

    ax.legend([h[i] for i in order], [l[i] for i in order],fontsize=15, ncol=3,
            loc='upper left', columnspacing=0.5,bbox_to_anchor=(0.05, 1.2))

    return fig, ax
# ─────────────────────────────────────────────────────────────────────────────
# Geometry Class
# ─────────────────────────────────────────────────────────────────────────────
class Geometry():
    def __init__(self, path: str):
        self.path = path
        
        self.load_geometry(path)
        self.compute_points()
    

    def load_geometry(self, path: str) -> dict[str, float]:
        """Read a tab-separated geometry file → dict of {str: float}."""
        geo = {}
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                # Support both tab-separated and whitespace-padded files.
                # Split on tab first; if that gives only one token, fall back
                # to splitting on the last run of whitespace before the value.
                if '\t' in line:
                    parts = line.split('\t', 1)
                else:
                    # rsplit on whitespace: key may contain spaces (e.g. "Top Tube")
                    # so split from the right to isolate the numeric value.
                    parts = line.rsplit(None, 1)
                if len(parts) >= 2:
                    try:
                        geo[parts[0].strip()] = float(parts[1].strip())
                    except ValueError:
                        pass
        self.geo = geo
        return geo
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Key-point computation
# ─────────────────────────────────────────────────────────────────────────────
 
    def compute_points(self) -> dict[str, np.ndarray]:
        """
        Return a dict of 2-D frame points (numpy float64 arrays).
    
        Derivations
        -----------
        BB drop     : both wheel axles are bb_drop mm ABOVE the BB centre.
                    rear_axle_x = -sqrt(chainstay^2 - bb_drop^2)
                    front_axle_x = front_centre (definition)
    
        Head tube   : top  = (Reach, Stack) by definition.
                    bottom = top + ht_len * (cos ha, -sin ha).
    
        Seat tube   : rises from BB at seat_angle from horizontal.
                    frame top = bb + seat_tube_cc * (-cos sa, sin sa)
    
        Saddle      : along the same seat-tube axis at seat_height from BB.
                    seat_pos = bb + seat_height * (-cos sa, sin sa)
    
        Stem        : clamps at ht_top (top of steerer / head tube).
                    Stem angle measured from horizontal, positive = drops downward.
                    stem_end = ht_top + stem_len * (cos(alpha), -sin(alpha))
    
        Handlebars  : bar centre = stem_end (bars go perpendicular to the bike plane).
                    Bar tips are at 3-D coords (stem_end_x, stem_end_y, +/-bar_width/2).
    
        Seat to bar-tip distance (3-D):
                    d = sqrt( dx^2 + dy^2 + (bar_width/2)^2 )
        """
        ha = np.radians(self.geo['Head Angle'])
        sa = np.radians(self.geo['Seat Angle'])
    
        bb = np.zeros(2)
    
        # ── Axles
        rear_axle  = np.array([
            -np.sqrt(self.geo['Chainstay']**2 - self.geo['BB Drop']**2),
            self.geo['BB Drop']
        ])
        front_axle = np.array([self.geo['Front Centre'], self.geo['BB Drop']])
    
        # ── Head tube
        ht_top    = np.array([self.geo['Reach'], self.geo['Stack']])
        ht_bottom = ht_top + self.geo['Head Tube'] * np.array([np.cos(ha), -np.sin(ha)])
    
        # ── Seat tube
        seat_tube_dir  = np.array([-np.cos(sa), np.sin(sa)])
        seat_frame_top = bb + self.geo['Seat Tube C-C'] * seat_tube_dir
    
        # Seat-stay junction ~50 mm below the seat cluster
        ss_h  = self.geo['Seat Tube C-C'] - min(50.0, self.geo['Seat Tube C-C'] * 0.10)
        ss_jn = bb + ss_h * seat_tube_dir
    
        # ── Saddle position (along seat tube at seat_height from BB)
        seat_pos = bb + self.geo['Seat height'] * seat_tube_dir
    
        # ── ETT origin
        ett_origin = np.array([self.geo['Reach'] - self.geo['Top Tube (effective)'], self.geo['Stack']])
    
        # ── Fork rake
        axis_dir  = np.array([ np.cos(ha), -np.sin(ha)])
        v         = front_axle - ht_bottom
        proj_len  = np.dot(v, axis_dir)
        rake_foot = ht_bottom + proj_len * axis_dir
    
        # ── Spacers: sit on the steerer above the head tube, below the stem.
        # The steerer runs along the head-tube axis reversed: (-cos ha, +sin ha)
        steerer_dir = np.array([-np.cos(ha), np.sin(ha)])
        spacer_top  = ht_top + self.geo.get('Spacers', 0.0) * steerer_dir
    
        # ── Stem clamps at the top of the spacer stack
        sa_stem  = np.radians(self.geo.get('Stem Angle', 0.0))
        stem_dir = np.array([np.cos(sa_stem), -np.sin(sa_stem)])
        stem_base = spacer_top
        stem_end  = stem_base + self.geo.get('Stem length', 0.0) * stem_dir
    
        # ── Handlebar / bar centre (2-D) = stem_end
        bar_centre = stem_end
    
        # ── Distances
        dx = stem_end[0] - seat_pos[0]
        dy = stem_end[1] - seat_pos[1]
        half_bar        = self.geo.get('Bar width', 0.0) / 2.0
        seat_to_bar_2d  = np.sqrt(dx**2 + dy**2)
        seat_to_bar_tip = np.sqrt(dx**2 + dy**2 + half_bar**2)
    
        self.points = dict(
            bb              = bb,
            rear_axle       = rear_axle,
            front_axle      = front_axle,
            ht_top          = ht_top,
            ht_bottom       = ht_bottom,
            seat_frame_top  = seat_frame_top,
            ss_jn           = ss_jn,
            seat_pos        = seat_pos,
            ett_origin      = ett_origin,
            rake_foot       = rake_foot,
            spacer_top      = spacer_top,
            stem_base       = stem_base,
            stem_end        = stem_end,
            bar_centre      = bar_centre,
            seat_to_bar_tip = seat_to_bar_tip,
            seat_to_bar_2d  = seat_to_bar_2d,
        ) 
        return self.points
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Drawing helpers
    # ─────────────────────────────────────────────────────────────────────────────
    
    def _tube(self, ax, a, b, color, lw=6, label=None, zorder=3, ls='-'):
        ax.plot([a[0], b[0]], [a[1], b[1]],
                color=color, lw=lw, solid_capstyle='round',
                zorder=zorder, ls=ls)
    
    
    def _ref(self, ax, p1, p2, color=None, ls='--'):
        c = color or PALETTE['ref_line']
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                color=c, lw=0.9, ls=ls, zorder=1)
    
    
    def _dim(self, ax, p1, p2, text, color='#777', off=(0, 0), fs=8.0, lw=1.2, zorder=6):
        mx = (p1[0]+p2[0])/2 + off[0]
        my = (p1[1]+p2[1])/2 + off[1]
        ax.annotate('', xy=tuple(p2), xytext=tuple(p1),
                    arrowprops=dict(arrowstyle='<->', color=color, lw=lw,
                                    mutation_scale=11),
                    zorder=zorder)
        ax.text(mx, my, text, ha='center', va='center', fontsize=fs,
                color=color, zorder=zorder+1,
                bbox=dict(fc='white', ec='none', pad=2.0, alpha=0.88))
    
    
    def _wheel(self, ax, centre, radius, n_spokes=16):
        ax.add_patch(plt.Circle(centre, radius, # type: ignore
                                color=PALETTE['wheel_tyre'], lw=14,
                                fill=False, zorder=2))
        ax.add_patch(plt.Circle(centre, radius - 13, # type: ignore
                                color=PALETTE['wheel_rim'], lw=1.8,
                                fill=False, zorder=2))
        angles = np.linspace(0, 2*np.pi, n_spokes, endpoint=False)
        for a in angles:
            spoke_end = centre + (radius - 13) * np.array([np.cos(a), np.sin(a)])
            ax.plot([centre[0], spoke_end[0]], [centre[1], spoke_end[1]],
                    color=PALETTE['spoke'], lw=0.5, zorder=2, alpha=0.6)
        ax.add_patch(plt.Circle(centre, 18, color='#888', zorder=4)) # type: ignore
        ax.add_patch(plt.Circle(centre, 10, color=PALETTE['point'], zorder=5)) # type: ignore
    
    
    def _saddle(self, ax, pos, sa_rad, saddle_w=120, color='k'):
        """Simplified saddle: platform + seatpost stub."""
        sx, sy = pos
        # Saddle platform (horizontal, slightly forward-biased)
        ax.plot([sx - saddle_w*0.35, sx + saddle_w*0.65], [sy, sy],
                color=color, lw=9, solid_capstyle='round', zorder=10)
        # Seatpost stub downward along seat-tube direction
        post_dir = np.array([-np.cos(sa_rad), np.sin(sa_rad)])
        post_end = pos - 65 * post_dir
        ax.plot([sx, post_end[0]], [sy, post_end[1]],
                color=color, lw=3.5, zorder=9)
        # Centre dot
        ax.plot(sx, sy, 'o', ms=7, color='white',          zorder=11)
        ax.plot(sx, sy, 'o', ms=3.5, color=color, zorder=12)
    
    
    def _handlebar(self, ax, centre):
        """
        In the 2-D side view the bar runs into the page.
        Render as a cross-circle symbol to indicate 'object coming toward viewer'.
        """
        cx, cy = centre
        ax.plot(cx, cy, 'o', ms=18, color=PALETTE['bar'],  zorder=12)
        ax.plot(cx, cy, 'o', ms=11, color='white',          zorder=13)
        ax.plot(cx, cy, 'o', ms=5,  color=PALETTE['bar'],   zorder=14)
        arm = 15
        ax.plot([cx-arm, cx+arm], [cy, cy],      color=PALETTE['bar'], lw=3, zorder=11)
        ax.plot([cx, cx],         [cy-arm, cy+arm], color=PALETTE['bar'], lw=3, zorder=11)
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    # Main plot
    # ─────────────────────────────────────────────────────────────────────────────
    
    def plot_bike(self, fig, ax, wheel_radius: int = WHEEL_RADIUS):
    
        ax.set_facecolor(PALETTE['bg'])
        fig.patch.set_facecolor(PALETTE['bg'])
    
        ground_y = self.points['rear_axle'][1] - wheel_radius
        x_left   = self.points['rear_axle'][0]  - wheel_radius - 100
        x_right  = self.points['front_axle'][0] + wheel_radius + 100
    
        ha_rad = np.radians(self.geo['Head Angle'])
        sa_rad = np.radians(self.geo['Seat Angle'])
    
        # ── Ground
        ax.fill_between([x_left, x_right], ground_y - 35, ground_y, color='#D6D6D6', zorder=0)
        ax.plot([x_left, x_right], [ground_y, ground_y], color=PALETTE['ground'], lw=2, zorder=1)
    
        # ── Wheels
        for axle in [self.points['rear_axle'], self.points['front_axle']]:
            self._wheel(ax, axle, wheel_radius)
    
        # ── Frame tubes
        self._tube(ax, self.points['bb'],             self.points['rear_axle'],      PALETTE['chainstay'], lw=8)
        self._tube(ax, self.points['rear_axle'],      self.points['ss_jn'],          PALETTE['seat_stay'], lw=7)
        self._tube(ax, self.points['bb'],             self.points['seat_frame_top'], PALETTE['seat_tube'], lw=8)
        self._tube(ax, self.points['seat_frame_top'], self.points['ht_top'],         PALETTE['top_tube'],  lw=7)
        self._tube(ax, self.points['bb'],             self.points['ht_bottom'],      PALETTE['down_tube'], lw=7)
        self._tube(ax, self.points['ht_top'],         self.points['ht_bottom'],      PALETTE['head_tube'], lw=12)
        self._tube(ax, self.points['ht_bottom'],      self.points['front_axle'],     PALETTE['fork'],      lw=7)

        # ── Spacer stack (steerer above head tube, below stem)
        self._tube(ax, self.points['ht_top'], self.points['spacer_top'], PALETTE['spacer'], lw=10, zorder=8)

        # ── Stem
        self._tube(ax, self.points['stem_base'], self.points['stem_end'], PALETTE['stem'], lw=6, zorder=9)
    
        # ── Saddle & handlebar
        self._saddle(ax, self.points['seat_pos'], sa_rad)
        self._handlebar(ax, self.points['bar_centre'])
    
        # ── BB shell
        ax.add_patch(plt.Circle(self.points['bb'], 28, color=PALETTE['bb_shell'], zorder=6)) # type: ignore
        ax.add_patch(plt.Circle(self.points['bb'], 14, color=PALETTE['point'],    zorder=7)) # type: ignore
    
        # ── Key-point labels
        kp = {
            'BB':                    (self.points['bb'],             (  32, -36), 'left'),
            'Rear axle':             (self.points['rear_axle'],      ( -15, -40), 'center'),
            'Front axle':            (self.points['front_axle'],     (   0, -40), 'center'),
            'Head tube\ntop':        (self.points['ht_top'],         (  45,  12), 'left'),
            'Head tube\nbottom':     (self.points['ht_bottom'],      (  45,  12), 'left'),
            'Seat cluster\n(frame)': (self.points['seat_frame_top'], ( -45,  12), 'right'),
            'Saddle':                (self.points['seat_pos'],       ( -60, -10), 'right'),
            'Handlebar\ncentre':     (self.points['bar_centre'],     (  48,  16), 'left'),
        }
        for lbl, (pt, off, ha_t) in kp.items():
            ax.annotate(lbl, xy=tuple(pt), xytext=(pt[0]+off[0], pt[1]+off[1]),
                        fontsize=7.2, color='#333', ha=ha_t,
                        arrowprops=dict(arrowstyle='-', color='#ccc', lw=0.8),
                        zorder=15)
    
        # ─────────────────────────────────────────────────────────────────────────
        # Dimension lines
        # ─────────────────────────────────────────────────────────────────────────
        bb  = self.points['bb'];    htt = self.points['ht_top'];  htb = self.points['ht_bottom']
        ra  = self.points['rear_axle'];  fa = self.points['front_axle']
        sft = self.points['seat_frame_top'];  eto = self.points['ett_origin'];  rft = self.points['rake_foot']
        spos = self.points['seat_pos'];  send = self.points['stem_end']
    
        perp_ha = np.array([ np.sin(ha_rad),  np.cos(ha_rad)])
        perp_sa = np.array([-np.sin(sa_rad), -np.cos(sa_rad)])
    
        # 1. Reach
        reach_target = np.array([htt[0], 0.0])
        self._ref(ax, bb, reach_target);  self._ref(ax, htt, reach_target)
        self._dim(ax, bb, reach_target, f"Reach\n{self.geo['Reach']:.0f} mm",
            color=PALETTE['dim_blue'], off=(0, -58))
    
        # 2. Stack
        self._dim(ax, np.array([htt[0], 0.0]), htt, f"Stack\n{self.geo['Stack']:.0f} mm",
            color=PALETTE['dim_blue'], off=(78, 0))
    
        # 3. BB Drop
        axle_level = np.array([0.0, ra[1]])
        self._ref(ax, ra, axle_level);  self._ref(ax, axle_level, bb)
        self._dim(ax, axle_level, bb, f"BB Drop\n{self.geo['BB Drop']:.0f} mm",
            color=PALETTE['dim_red'], off=(-75, 0))
    
        # 4. Wheelbase
        wb_y = ground_y - 50
        self._ref(ax, ra, np.array([ra[0], wb_y]));  self._ref(ax, fa, np.array([fa[0], wb_y]))
        self._dim(ax, np.array([ra[0], wb_y]), np.array([fa[0], wb_y]),
            f"Wheelbase  {self.geo['Wheelbase']:.0f} mm",
            color=PALETTE['dim_grey'], off=(0, -22))
    
        # 5. Effective top tube
        ett_y    = htt[1] + 65
        self._ref(ax, eto, np.array([eto[0], ett_y]));  self._ref(ax, htt, np.array([htt[0], ett_y]))
        self._dim(ax, np.array([eto[0], ett_y]), np.array([htt[0], ett_y]),
            f"Effective top tube  {self.geo['Top Tube (effective)']:.0f} mm",
            color=PALETTE['dim_blue'], off=(0, 22))
    
        # 6. Seat tube C-C (frame)
        self._dim(ax, bb, sft, f"Seat tube C-C\n{self.geo['Seat Tube C-C']:.0f} mm",
            color=PALETTE['dim_red'], off=perp_sa * 95)
    
        # 7. Seat height (along seat tube, further offset)
        self._dim(ax, bb, spos, f"Seat height\n{self.geo['Seat height']:.0f} mm",
            color='#7B241C', off=perp_sa * 175)
    
        # 8. Head tube length
        self._dim(ax, htt, htb, f"HT {self.geo['Head Tube']:.0f} mm",
            color=PALETTE['dim_orange'], off=perp_ha * 55)
    
        # 9. Chainstay label
        cs_mid = (bb + ra) / 2
        ax.text(cs_mid[0], cs_mid[1] - 26,
                f"Chainstay  {self.geo['Chainstay']:.0f} mm",
                ha='center', fontsize=8, color='#7D3C98', style='italic', zorder=8)
    
        # 10. Front centre
        fc_y = (bb[1] + fa[1]) / 2 - 42
        self._ref(ax, bb, np.array([bb[0], fc_y]));  self._ref(ax, fa, np.array([fa[0], fc_y]))
        self._dim(ax, np.array([bb[0], fc_y]), np.array([fa[0], fc_y]),
            f"Front centre  {self.geo['Front Centre']:.0f} mm",
            color=PALETTE['dim_grey'], off=(0, -20))
    
        # 11. Fork rake
        self._ref(ax, rft, fa, color='#D4862A')
        self._dim(ax, rft, fa, f"Rake\n{self.geo['Fork Rake / Offset']:.0f} mm",
            color=PALETTE['dim_orange'], off=(32, -10))
    
        # 12. Stem length
        self._dim(ax, self.points['stem_base'], self.points['stem_end'],
            f"Stem {self.geo.get('Stem length',0):.0f} mm",
            color=PALETTE['dim_red'], off=(0, 30))
    
        # 12b. Spacer stack dimension
        spacers_mm = self.geo.get('Spacers', 0.0)
        if spacers_mm > 0:
            self._dim(ax, self.points['ht_top'], self.points['spacer_top'],
                f"Spacers\n{spacers_mm:.0f} mm",
                color=PALETTE['spacer'], off=perp_ha * 80)
    
        # 13. Stem angle arc
        stem_arc_r = 55
        stem_angle  = self.geo.get('Stem Angle', 0.0)
        ax.add_patch(Arc(tuple(self.points['stem_base']), 2*stem_arc_r, 2*stem_arc_r,
                        angle=0, theta1=-stem_angle, theta2=0.0,
                        color=PALETTE['dim_red'], lw=1.6, zorder=7))
        ax.text(self.points['stem_base'][0] + stem_arc_r + 6, self.points['stem_base'][1] - 14,
                f"{stem_angle:.0f}°", fontsize=7.5, color=PALETTE['dim_red'], zorder=10)
    
        # 14. Bar width annotation (out-of-plane)
        bx, by = self.points['stem_end']
        ax.annotate(f"Bar width {self.geo.get('Bar width',0):.0f} mm\n(perpendicular to view)",
                    xy=(bx, by), xytext=(bx + 65, by - 65),
                    fontsize=7.5, color=PALETTE['dim_grey'], ha='left',
                    arrowprops=dict(arrowstyle='->', color=PALETTE['dim_grey'], lw=0.9),
                    zorder=15)
    
        # 15. Seat → handlebar / bar-tip distance
        self._ref(ax, self.points['seat_pos'], self.points['stem_end'], color=PALETTE['dim_green'], ls=':')
        mid = (self.points['seat_pos'] + self.points['stem_end']) / 2
        print(f"Seat → bar tip (3-D)\n",
            f"In-plane: {self.points['seat_to_bar_2d']:.0f} mm\n",
            f"+ ½ bar:  {self.points['seat_to_bar_tip']:.0f} mm",)
        ax.annotate(
            f"Seat → bar tip (3-D)\n"
            f"In-plane: {self.points['seat_to_bar_2d']:.0f} mm\n"
            f"+ ½ bar:  {self.points['seat_to_bar_tip']:.0f} mm",
            xy=(0.1,0.8),
            xytext=(0.1,0.9),
            textcoords=ax.transAxes,
            fontsize=8.5, color=PALETTE['dim_green'], ha='center',
            bbox=dict(fc='white', ec=PALETTE['dim_green'],
                    boxstyle='round,pad=0.55', lw=1.3, alpha=0.94),
            #arrowprops=dict(arrowstyle='->', color=PALETTE['dim_green'], lw=1.2),
            zorder=16,
        )
    
        # 16. Head angle arc
        arc_r = 90
        ax.add_patch(Arc(tuple(htb), 2*arc_r, 2*arc_r,
                        angle=0, theta1=180.0 - self.geo['Head Angle'], theta2=180.0,
                        color=PALETTE['dim_orange'], lw=1.8, zorder=7))
        ax.text(htb[0] - arc_r - 10, htb[1] + arc_r * 0.3,
                f"Head angle\n{self.geo['Head Angle']:.0f}°",
                fontsize=8.5, color=PALETTE['dim_orange'], ha='right', zorder=10)
    
        # 17. Seat angle arc
        ax.add_patch(Arc(tuple(bb), 2*arc_r, 2*arc_r,
                        angle=0, theta1=180.0 - self.geo['Seat Angle'], theta2=180.0,
                        color=PALETTE['dim_red'], lw=1.8, zorder=7))
        ax.text(bb[0] - arc_r - 12, bb[1] + arc_r * 0.55,
                f"Seat angle\n{self.geo['Seat Angle']:.1f}°",
                fontsize=8.5, color=PALETTE['dim_red'], ha='right', zorder=10)
    
    
        ax.set_aspect('equal')
        ax.set_xlabel('mm   (x  →  toward front wheel)', fontsize=15, labelpad=8)
        ax.set_ylabel('mm   (y  ↑  upward)', fontsize=15, labelpad=8)
        ax.set_title('Bicycle Frame Geometry', fontsize=16, fontweight='bold', pad=16)
        ax.grid(True, alpha=0.18, zorder=0)
        ax.tick_params(labelsize=9)
    
        plt.tight_layout()
        return fig
 
    def plot_comp(self, fig, ax,path,  wheel_radius: int = WHEEL_RADIUS, color='k'):
        """Plot a comparison view with two bikes overlaid."""

        self.load_geometry(path)
        self.compute_points()

        ax.set_facecolor(PALETTE['bg'])
        fig.patch.set_facecolor(PALETTE['bg'])
    
        ground_y = self.points['rear_axle'][1] - wheel_radius
        x_left   = self.points['rear_axle'][0]  - wheel_radius - 100
        x_right  = self.points['front_axle'][0] + wheel_radius + 100
    
        ha_rad = np.radians(self.geo['Head Angle'])
        sa_rad = np.radians(self.geo['Seat Angle'])
    
        # ── Ground
        ax.fill_between([x_left, x_right], ground_y - 35, ground_y, color='#D6D6D6', zorder=0)
        ax.plot([x_left, x_right], [ground_y, ground_y], color=PALETTE['ground'], lw=2, zorder=1)
    
        # ── Wheels
        for axle in [self.points['rear_axle'], self.points['front_axle']]:
            self._wheel(ax, axle, wheel_radius)
    
        # ── Frame tubes
        self._tube(ax, self.points['bb'],             self.points['rear_axle'],      color, lw=8)
        self._tube(ax, self.points['rear_axle'],      self.points['ss_jn'],         color, lw=7)
        self._tube(ax, self.points['bb'],             self.points['seat_frame_top'], color, lw=8)
        self._tube(ax, self.points['seat_frame_top'], self.points['ht_top'],         color, lw=7)
        self._tube(ax, self.points['bb'],             self.points['ht_bottom'],      color, lw=7)
        self._tube(ax, self.points['ht_top'],         self.points['ht_bottom'],      color, lw=12)
        self._tube(ax, self.points['ht_bottom'],      self.points['front_axle'],     color, lw=7)

        # ── Spacer stack (steerer above head tube, below stem)
        self._tube(ax, self.points['ht_top'], self.points['spacer_top'], color, lw=10, zorder=8)

        # ── Stem
        self._tube(ax, self.points['stem_base'], self.points['stem_end'], color, lw=6, zorder=9)
    
        # ── Saddle & handlebar
        self._saddle(ax, self.points['seat_pos'], sa_rad, color=color)
        self._handlebar(ax, self.points['bar_centre'])
    
        # ── BB shell
        ax.add_patch(plt.Circle(self.points['bb'], 28, color=PALETTE['bb_shell'], zorder=6))  # pyright: ignore[reportAttributeAccessIssue]
        ax.add_patch(plt.Circle(self.points['bb'], 14, color=PALETTE['point'],    zorder=7)) # pyright: ignore[reportAttributeAccessIssue]
    
    
        ax.set_aspect('equal')
        ax.set_xlabel('mm   (x  →  toward front wheel)', fontsize=10, labelpad=8)
        ax.set_ylabel('mm   (y  ↑  upward)', fontsize=10, labelpad=8)
        ax.grid(True, alpha=0.18, zorder=0)
        ax.tick_params(labelsize=9)

        plt.tight_layout()
        return fig

    # ─────────────────────────────────────────────────────────────────────────────
    # 3-D plot
    # ─────────────────────────────────────────────────────────────────────────────

    def plot_bike_3D(self, fig, ax=None, wheel_radius: int = WHEEL_RADIUS):
        """
        3-D view of the bike.

        Coordinate system:
            x  →  toward front wheel
            y  ↑  upward
            z  →  toward right (drive side)

        The frame lives in the z = 0 plane.
        Wheels are circles perpendicular to the x-axis.
        Handlebars and saddle extend in ±z.

        A 3-D axes is created automatically from fig; any 2-D axes passed in
        as ax is ignored.
        """
        fig.clf()
        ax = fig.add_subplot(111, projection='3d')

        ax.set_facecolor(PALETTE['bg'])
        fig.patch.set_facecolor(PALETTE['bg'])

        sa_rad   = np.radians(self.geo['Seat Angle'])
        half_bar = self.geo.get('Bar width', 420) / 2.0
        saddle_hw = 65      # half lateral saddle width
        bb_w      = 68      # standard road BB shell width

        # ── Helper: 3-D tube
        def tube3(a3, b3, color, lw=4):
            ax.plot([a3[0], b3[0]], [a3[2], b3[2]], [a3[1], b3[1]],
                    color=color, lw=lw, solid_capstyle='round')

        # ── Helper: 2-D point → 3-D (z = 0 for frame plane)
        def p3(pt2d, z=0.0):
            return np.array([pt2d[0], pt2d[1], z])

        # ── Helper: wheel circle in the x-y plane (direction of travel × vertical)
        #           tyre has thickness in z (lateral)
        def wheel3(cx, axle_y, radius, n=120):
            theta  = np.linspace(0, 2 * np.pi, n)
            xr     = cx + radius * np.cos(theta)
            yr     = axle_y + radius * np.sin(theta)
            half_tw = 13   # half tyre width in z
            # Tyre edges at ±z
            for z_side in [-half_tw, half_tw]:
                ax.plot(xr, np.full(n, z_side), yr,
                        color=PALETTE['wheel_tyre'], lw=4)
            # Rim at z = 0
            rim_r = radius - 13
            xrr = cx + rim_r * np.cos(theta)
            yrr = axle_y + rim_r * np.sin(theta)
            ax.plot(xrr, np.zeros(n), yrr,
                    color=PALETTE['wheel_rim'], lw=1.5, alpha=0.7)
            # Spokes
            for a in np.linspace(0, 2 * np.pi, 16, endpoint=False):
                sx = cx + rim_r * np.cos(a)
                sy = axle_y + rim_r * np.sin(a)
                ax.plot([cx, sx], [0, 0], [axle_y, sy],
                        color=PALETTE['spoke'], lw=0.5, alpha=0.5)

        pts = self.points

        # ── Ground plane
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        ground_y = pts['rear_axle'][1] - wheel_radius
        x_l = pts['rear_axle'][0]  - wheel_radius - 100
        x_r = pts['front_axle'][0] + wheel_radius + 100
        z_w = wheel_radius * 0.45
        ground_verts = [[(x_l, -z_w, ground_y), (x_r, -z_w, ground_y),
                         (x_r,  z_w, ground_y), (x_l,  z_w, ground_y)]]
        ground_poly = Poly3DCollection(ground_verts, alpha=0.45, facecolor='#D6D6D6', edgecolor='none')
        ax.add_collection(ground_poly)

        # ── Wheels
        for axle in [pts['rear_axle'], pts['front_axle']]:
            wheel3(axle[0], axle[1], wheel_radius)

        # ── Frame tubes
        frame_tubes = [
            (pts['bb'],             pts['rear_axle'],      PALETTE['chainstay'], 6),
            (pts['rear_axle'],      pts['ss_jn'],          PALETTE['seat_stay'], 5),
            (pts['bb'],             pts['seat_frame_top'], PALETTE['seat_tube'], 6),
            (pts['seat_frame_top'], pts['ht_top'],         PALETTE['top_tube'],  5),
            (pts['bb'],             pts['ht_bottom'],      PALETTE['down_tube'], 5),
            (pts['ht_top'],         pts['ht_bottom'],      PALETTE['head_tube'], 9),
            (pts['ht_bottom'],      pts['front_axle'],     PALETTE['fork'],      5),
        ]
        for a2, b2, col, lw in frame_tubes:
            tube3(p3(a2), p3(b2), col, lw=lw)

        # ── Spacers & stem
        tube3(p3(pts['ht_top']),    p3(pts['spacer_top']), PALETTE['spacer'], lw=8)
        tube3(p3(pts['stem_base']), p3(pts['stem_end']),   PALETTE['stem'],   lw=5)

        # ── BB shell (cylinder along z)
        bb = pts['bb']
        ax.plot([bb[0], bb[0]], [-bb_w / 2, bb_w / 2], [bb[1], bb[1]],
                color=PALETTE['bb_shell'], lw=14, solid_capstyle='round')

        # ── Handlebars (±z from stem_end)
        se = pts['stem_end']
        ax.plot([se[0], se[0]], [-half_bar, half_bar], [se[1], se[1]],
                color=PALETTE['bar'], lw=7, solid_capstyle='round')
        for z_bar in [-half_bar, half_bar]:
            ax.plot([se[0]], [z_bar], [se[1]], 'o', color=PALETTE['bar'], ms=8)

        # ── Saddle platform (±z) and seatpost stub
        sp = pts['seat_pos']
        ax.plot([sp[0] - 120 * 0.35, sp[0] + 120 * 0.65],
                [0, 0], [sp[1], sp[1]],
                color=PALETTE['saddle'], lw=9, solid_capstyle='round')
        ax.plot([sp[0], sp[0]], [-saddle_hw, saddle_hw], [sp[1], sp[1]],
                color=PALETTE['saddle'], lw=5, solid_capstyle='round', alpha=0.7)
        post_dir = np.array([-np.cos(sa_rad), np.sin(sa_rad)])
        post_end = sp - 65 * post_dir
        tube3(p3(sp), p3(post_end), '#555', lw=3)

        # ── Axes & style
        ax.set_xlabel('x  (→ front)', fontsize=9, labelpad=6)
        ax.set_ylabel('z  (→ right)', fontsize=9, labelpad=6)
        ax.set_zlabel('y  (↑ up)',    fontsize=9, labelpad=6)
        ax.set_title('Bicycle Frame Geometry – 3-D View',
                     fontsize=14, fontweight='bold', pad=14)

        # Equal-ish aspect ratio
        all_x = [pts['rear_axle'][0] - wheel_radius, pts['front_axle'][0] + wheel_radius]
        all_y = [ground_y, pts['ht_top'][1] + 80]
        max_range = max(all_x[1] - all_x[0], all_y[1] - all_y[0], 2 * half_bar) / 2
        mid_x = (all_x[0] + all_x[1]) / 2
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(-max_range, max_range)
        ax.set_zlim(all_y[0], all_y[0] + 2 * max_range)

        ax.grid(True, alpha=0.15)
        ax.tick_params(labelsize=8)

        return fig
