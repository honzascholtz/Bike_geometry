#!/usr/bin/env python3
"""
gui.py  –  Tkinter GUI for FrameStack bike geometry visualiser.

Modes
-----
  2D Single     : Full annotated side-view of one bike (plot_bike)
  2D Comparison : Multiple bikes overlaid with colour coding (plot_comparison)
  3D            : Interactive 3-D view of one bike (plot_bike_3D)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import FrameStack as fs

# ── Preset colours used when adding bikes to the comparison list ──────────────
PRESET_COLORS = [
    '#2980B9', '#E74C3C', '#27AE60', '#E67E22',
    '#8E44AD', '#16A085', '#F39C12', '#C0392B',
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('FrameStack – Bike Geometry Viewer')
        self.geometry('1280x780')
        self.minsize(900, 600)

        # ── State ──────────────────────────────────────────────────────────────
        self.mode = tk.StringVar(value='single')   # 'single' | 'compare' | '3d'
        self.bikes: list[dict] = []                # [{path, name, color}, ...]
        self.selected_index = tk.IntVar(value=-1)  # which bike is "active"

        self._build_ui()
        self._new_figure()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self, relief='flat', padding=4)
        toolbar.pack(side='top', fill='x')
        self._build_toolbar(toolbar)

        # Main pane: left sidebar + canvas
        pane = ttk.PanedWindow(self, orient='horizontal')
        pane.pack(fill='both', expand=True, padx=4, pady=(0, 4))

        sidebar = ttk.Frame(pane, width=240)
        sidebar.pack_propagate(False)
        pane.add(sidebar, weight=0)

        canvas_frame = ttk.Frame(pane)
        pane.add(canvas_frame, weight=1)

        self._build_sidebar(sidebar)
        self._build_canvas_area(canvas_frame)

        # Status bar
        self.status_var = tk.StringVar(value='Open a geometry file to get started.')
        ttk.Label(self, textvariable=self.status_var, anchor='w',
                  relief='sunken', padding=(6, 2)).pack(side='bottom', fill='x')

    def _build_toolbar(self, parent):
        # File actions
        ttk.Button(parent, text='Open file…', padding=(10, 6),
                   command=self._open_single).pack(side='left', padx=2)
        ttk.Button(parent, text='Add to comparison…', padding=(10, 6),
                   command=self._add_comparison).pack(side='left', padx=2)
        ttk.Button(parent, text='Clear all', padding=(10, 6),
                   command=self._clear_all).pack(side='left', padx=2)

        ttk.Separator(parent, orient='vertical').pack(side='left', fill='y', padx=8)

        # View mode
        ttk.Label(parent, text='View:').pack(side='left')
        for label, val in [('2D single', 'single'), ('Comparison', 'compare'), ('3D', '3d')]:
            ttk.Radiobutton(parent, text=label, variable=self.mode, value=val,
                            padding=(6, 6),
                            command=self._refresh_plot).pack(side='left', padx=2)

        ttk.Separator(parent, orient='vertical').pack(side='left', fill='y', padx=8)
        ttk.Button(parent, text='Save figure…', padding=(10, 6),
                   command=self._save_figure).pack(side='left', padx=2)

    def _build_sidebar(self, parent):
        ttk.Label(parent, text='Loaded bikes', font=('', 10, 'bold'),
                  padding=(4, 6, 4, 2)).pack(fill='x')

        # Listbox with scrollbar
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=4)

        sb = ttk.Scrollbar(frame)
        sb.pack(side='right', fill='y')
        self.listbox = tk.Listbox(frame, yscrollcommand=sb.set, activestyle='dotbox',
                                  selectmode='single', font=('', 9))
        self.listbox.pack(fill='both', expand=True)
        sb.config(command=self.listbox.yview)
        self.listbox.bind('<<ListboxSelect>>', self._on_list_select)

        # Per-bike controls
        btn_frame = ttk.Frame(parent, padding=(4, 4))
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text='Rename', padding=(0, 6),
                   command=self._rename_bike).pack(side='left', expand=True, fill='x', padx=1)
        ttk.Button(btn_frame, text='Colour', padding=(0, 6),
                   command=self._change_color).pack(side='left', expand=True, fill='x', padx=1)
        ttk.Button(btn_frame, text='Remove', padding=(0, 6),
                   command=self._remove_bike).pack(side='left', expand=True, fill='x', padx=1)

        ttk.Separator(parent, orient='horizontal').pack(fill='x', padx=4, pady=6)

        # Geometry table
        ttk.Label(parent, text='Geometry', font=('', 10, 'bold'),
                  padding=(4, 0, 4, 2)).pack(fill='x')

        tbl_frame = ttk.Frame(parent)
        tbl_frame.pack(fill='both', expand=True, padx=4, pady=(0, 4))

        vsb = ttk.Scrollbar(tbl_frame)
        vsb.pack(side='right', fill='y')
        self.geo_tree = ttk.Treeview(tbl_frame, columns=('key', 'value'),
                                     show='headings', yscrollcommand=vsb.set,
                                     height=14)
        self.geo_tree.heading('key',   text='Parameter')
        self.geo_tree.heading('value', text='Value (mm / °)')
        self.geo_tree.column('key',   width=140, anchor='w')
        self.geo_tree.column('value', width=70,  anchor='e')
        self.geo_tree.pack(fill='both', expand=True)
        vsb.config(command=self.geo_tree.yview)

    def _build_canvas_area(self, parent):
        self.canvas_frame = parent

    # ── Figure management ─────────────────────────────────────────────────────

    def _new_figure(self, fig=None):
        """Replace the embedded canvas with a new (or given) figure."""
        # Destroy old canvas widgets
        for widget in self.canvas_frame.winfo_children():
            widget.destroy()

        if fig is None:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.set_visible(False)
            ax.set_facecolor('#F7F7F7')
            fig.patch.set_facecolor('#F7F7F7')

        self.fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        nav = NavigationToolbar2Tk(self.canvas, self.canvas_frame)
        nav.update()

    # ── File I/O ──────────────────────────────────────────────────────────────

    def _open_single(self):
        path = filedialog.askopenfilename(
            title='Open geometry file',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')],
            initialdir='Geometry_files',
        )
        if not path:
            return
        name = self._default_name(path)
        color = PRESET_COLORS[len(self.bikes) % len(PRESET_COLORS)]
        self.bikes.clear()
        self.bikes.append(dict(path=path, name=name, color=color))
        self.mode.set('single')
        self._sync_listbox()
        self.listbox.selection_set(0)
        self._on_list_select()
        self._refresh_plot()

    def _add_comparison(self):
        paths = filedialog.askopenfilenames(
            title='Add bikes to comparison',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')],
            initialdir='Geometry_files',
        )
        if not paths:
            return
        for path in paths:
            name  = self._default_name(path)
            color = PRESET_COLORS[len(self.bikes) % len(PRESET_COLORS)]
            self.bikes.append(dict(path=path, name=name, color=color))
        if len(self.bikes) > 1:
            self.mode.set('compare')
        self._sync_listbox()
        self.listbox.selection_set(len(self.bikes) - 1)
        self._on_list_select()
        self._refresh_plot()

    def _clear_all(self):
        self.bikes.clear()
        self._sync_listbox()
        self._clear_geo_table()
        self._new_figure()
        self.status_var.set('Cleared.')

    # ── Bike list controls ────────────────────────────────────────────────────

    def _on_list_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.selected_index.set(idx)
        self._populate_geo_table(self.bikes[idx]['path'])

    def _rename_bike(self):
        idx = self._current_index()
        if idx is None:
            return
        win = tk.Toplevel(self)
        win.title('Rename bike')
        win.resizable(False, False)
        ttk.Label(win, text='Name:', padding=8).grid(row=0, column=0, sticky='w')
        entry = ttk.Entry(win, width=28)
        entry.insert(0, self.bikes[idx]['name'])
        entry.grid(row=0, column=1, padx=(0, 8), pady=8)
        entry.focus()

        def _apply():
            self.bikes[idx]['name'] = entry.get().strip() or self.bikes[idx]['name']
            win.destroy()
            self._sync_listbox()
            self._refresh_plot()

        entry.bind('<Return>', lambda _: _apply())
        ttk.Button(win, text='OK', command=_apply).grid(
            row=1, column=0, columnspan=2, pady=(0, 8))

    def _change_color(self):
        idx = self._current_index()
        if idx is None:
            return
        result = colorchooser.askcolor(
            color=self.bikes[idx]['color'], title='Pick colour')
        if result and result[1]:
            self.bikes[idx]['color'] = result[1]
            self._sync_listbox()
            self._refresh_plot()

    def _remove_bike(self):
        idx = self._current_index()
        if idx is None:
            return
        self.bikes.pop(idx)
        self._sync_listbox()
        self._clear_geo_table()
        if self.bikes:
            new_idx = min(idx, len(self.bikes) - 1)
            self.listbox.selection_set(new_idx)
            self._on_list_select()
        self._refresh_plot()

    def _current_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _sync_listbox(self):
        self.listbox.delete(0, 'end')
        for bike in self.bikes:
            self.listbox.insert('end', bike['name'])

    # ── Geometry table ────────────────────────────────────────────────────────

    def _populate_geo_table(self, path: str):
        self._clear_geo_table()
        try:
            geo = fs.FrameStack(path).geo
        except Exception as exc:
            self.status_var.set(f'Error reading file: {exc}')
            return
        for key, val in geo.items():
            display = f'{val:.1f}' if isinstance(val, float) else str(val)
            self.geo_tree.insert('', 'end', values=(key, display))

    def _clear_geo_table(self):
        for row in self.geo_tree.get_children():
            self.geo_tree.delete(row)

    # ── Plot rendering ────────────────────────────────────────────────────────

    def _refresh_plot(self):
        if not self.bikes:
            self._new_figure()
            self.status_var.set('No bikes loaded.')
            return

        plt.close('all')
        mode = self.mode.get()

        try:
            if mode == 'single':
                self._plot_single()
            elif mode == 'compare':
                self._plot_compare()
            elif mode == '3d':
                self._plot_3d()
        except Exception as exc:
            messagebox.showerror('Plot error', str(exc))
            self.status_var.set(f'Error: {exc}')

    def _plot_single(self):
        idx = self._current_index()
        bike = self.bikes[idx if idx is not None else 0]
        fig, ax = plt.subplots(figsize=(10, 6))
        geo = fs.FrameStack(bike['path'])
        geo.plot_bike(fig, ax)
        self._new_figure(fig)
        self.status_var.set(f'2D view: {bike["name"]}')

    def _plot_compare(self):
        if len(self.bikes) < 2:
            self.status_var.set('Add at least 2 bikes for comparison.')
            self._plot_single()
            return
        paths  = [b['path']  for b in self.bikes]
        names  = [b['name']  for b in self.bikes]
        colors = [b['color'] for b in self.bikes]
        fig, ax = fs.plot_comparison(paths, colors=colors, names=names)
        ax.set_title('Bike Geometry Comparison', fontsize=16, fontweight='bold', pad=16)
        self._new_figure(fig)
        self.status_var.set(f'Comparing {len(self.bikes)} bikes.')

    def _plot_3d(self):
        idx = self._current_index()
        bike = self.bikes[idx if idx is not None else 0]
        fig = plt.figure(figsize=(10, 7))
        geo = fs.FrameStack(bike['path'])
        geo.plot_bike_3D(fig)
        self._new_figure(fig)
        self.status_var.set(f'3D view: {bike["name"]}')

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_figure(self):
        if not hasattr(self, 'fig'):
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG', '*.png'), ('PDF', '*.pdf'), ('SVG', '*.svg')],
        )
        if path:
            self.fig.savefig(path, dpi=180, bbox_inches='tight')
            self.status_var.set(f'Saved to {path}')

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _default_name(path: str) -> str:
        import os
        return os.path.splitext(os.path.basename(path))[0].replace('_', ' ')


if __name__ == '__main__':
    app = App()
    app.mainloop()
