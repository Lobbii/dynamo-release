"""Mapping Vector Field of Single Cells
"""

# from .theme import points
from .utils import quiver_autoscaler
from .scatters import scatters

from .preprocess import show_fraction, feature_genes, variance_explained

from .dynamics import phase_portraits, dynamics
from .time_series import kinetic_heatmap, kinetic_curves

from .dimension_reduction import pca, tsne, umap, trimap
from .connectivity import nneighbors

from .scVectorField import cell_wise_velocity, grid_velocity, streamline_plot, line_integral_conv # , plot_LIC_gray
from .topology import plot_flow_field, plot_fixed_points, plot_nullclines, plot_separatrix, plot_traj, topography

from .scPotential import show_landscape
