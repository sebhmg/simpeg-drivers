#  Copyright (c) 2023 Mira Geoscience Ltd.
#
#  This file is part of geoapps.
#
#  geoapps is distributed under the terms and conditions of the MIT License
#  (see LICENSE file at the root of this source code package).


from __future__ import annotations

from pathlib import Path

from discretize import TreeMesh
from geoh5py.workspace import Workspace

from simpeg_drivers.components import (
    InversionData,
    InversionMesh,
    InversionTopography,
)
from simpeg_drivers.potential_fields import MagneticVectorParams
from simpeg_drivers.utils.testing import Geoh5Tester

from tests import GEOH5 as geoh5

def setup_params(tmp):
    geotest = Geoh5Tester(geoh5, tmp, "test.geoh5", MagneticVectorParams)
    geotest.set_param("mesh", "{a8f3b369-10bd-4ca8-8bd6-2d2595bddbdf}")
    geotest.set_param("data_object", "{538a7eb1-2218-4bec-98cc-0a759aa0ef4f}")
    geotest.set_param("topography_object", "{ab3c2083-6ea8-4d31-9230-7aad3ec09525}")
    geotest.set_param("tmi_channel", "{44822654-b6ae-45b0-8886-2d845f80f422}")
    geotest.set_param("topography", "{a603a762-f6cb-4b21-afda-3160e725bf7d}")
    return geotest.make()


def test_initialize(tmp_path: Path):
    ws, params = setup_params(tmp_path)
    inversion_data = InversionData(ws, params)
    inversion_topography = InversionTopography(ws, params)
    inversion_mesh = InversionMesh(ws, params, inversion_data, inversion_topography)
    assert isinstance(inversion_mesh.mesh, TreeMesh)
