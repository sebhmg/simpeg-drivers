# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
#  Copyright (c) 2023-2024 Mira Geoscience Ltd.
#  All rights reserved.
#
#  This file is part of simpeg-drivers.
#
#  The software and information contained herein are proprietary to, and
#  comprise valuable trade secrets of, Mira Geoscience, which
#  intend to preserve as trade secrets such software and information.
#  This software is furnished pursuant to a written license agreement and
#  may be used, copied, transmitted, and stored only in accordance with
#  the terms of such license and with the inclusion of the above copyright
#  notice.  This software and information or any other copies thereof may
#  not be provided or otherwise made available to any other person.
#
# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

from pathlib import Path

import numpy as np
from geoh5py.objects import Octree
from geoh5py.workspace import Workspace

from simpeg_drivers.joint.joint_surveys import JointSurveysParams
from simpeg_drivers.joint.joint_surveys.driver import JointSurveyDriver
from simpeg_drivers.potential_fields import GravityParams
from simpeg_drivers.potential_fields.gravity.driver import GravityDriver
from simpeg_drivers.utils.testing import check_target, setup_inversion_workspace
from simpeg_drivers.utils.utils import get_inversion_output


# To test the full run and validate the inversion.
# Move this file out of the test directory and run.

target_run = {"data_norm": 0.2997791602206556, "phi_d": 705.3, "phi_m": 74.54}


def test_joint_surveys_fwr_run(
    tmp_path,
    n_grid_points=6,
    refinement=(2,),
):
    # Create local problem A
    geoh5, _, model, survey, topography = setup_inversion_workspace(
        tmp_path,
        background=0.0,
        anomaly=0.75,
        refinement=refinement,
        n_electrodes=n_grid_points,
        n_lines=n_grid_points,
    )
    params = GravityParams(
        forward_only=True,
        geoh5=geoh5,
        mesh=model.parent.uid,
        topography_object=topography.uid,
        resolution=0.0,
        z_from_topo=False,
        data_object=survey.uid,
        starting_model=model.uid,
    )
    fwr_driver_a = GravityDriver(params)
    fwr_driver_a.out_group.name = "Gravity Forward [0]"

    # Create local problem B
    _, _, model, survey, _ = setup_inversion_workspace(
        tmp_path,
        background=0.0,
        anomaly=0.75,
        refinement=[0, 2],
        n_electrodes=int(n_grid_points / 2),
        n_lines=int(n_grid_points / 2),
        flatten=False,
        geoh5=geoh5,
        drape_height=10.0,
    )
    params = GravityParams(
        forward_only=True,
        geoh5=geoh5,
        mesh=model.parent.uid,
        topography_object=topography.uid,
        resolution=0.0,
        z_from_topo=False,
        data_object=survey.uid,
        starting_model=model.uid,
    )
    fwr_driver_b = GravityDriver(params)
    fwr_driver_b.out_group.name = "Gravity Forward [1]"

    # Force co-location of meshes
    fwr_driver_b.inversion_mesh.entity.origin = (
        fwr_driver_a.inversion_mesh.entity.origin
    )
    fwr_driver_b.workspace.update_attribute(
        fwr_driver_b.inversion_mesh.entity, "attributes"
    )
    fwr_driver_b.inversion_mesh._mesh = None  # pylint: disable=protected-access
    fwr_driver_a.run()
    fwr_driver_b.run()
    geoh5.close()


def test_joint_surveys_inv_run(
    tmp_path,
    max_iterations=1,
    unittest=True,
):
    workpath = tmp_path / "inversion_test.ui.geoh5"
    if unittest:
        workpath = (
            tmp_path.parent / "test_joint_surveys_fwr_run0" / "inversion_test.ui.geoh5"
        )

    with Workspace(workpath) as geoh5:
        topography = geoh5.get_entity("topography")[0]
        drivers = []
        orig_data = []
        mesh = None
        for ind in range(2):
            group = geoh5.get_entity(f"Gravity Forward [{ind}]")[0]
            survey = geoh5.get_entity(group.options["data_object"]["value"])[0]
            mesh = None
            for child in group.children:
                if isinstance(child, Octree):
                    mesh = child
                else:
                    survey = child

            if mesh is None:
                raise ValueError("No mesh found in the group.")

            gz = survey.get_data("Iteration_0_gz")[0]
            orig_data.append(gz.values)
            params = GravityParams(
                geoh5=geoh5,
                mesh=mesh.uid,
                topography_object=topography.uid,
                data_object=survey.uid,
                gz_channel=gz.uid,
                gz_uncertainty=np.var(gz.values) * 2.0,
                starting_model=0.0,
            )
            drivers.append(GravityDriver(params))

        # Run the inverse
        joint_params = JointSurveysParams(
            geoh5=geoh5,
            topography_object=topography.uid,
            mesh=drivers[0].params.mesh,
            group_a=drivers[0].params.out_group,
            group_b=drivers[1].params.out_group,
            starting_model=1e-4,
            reference_model=0.0,
            s_norm=0.0,
            x_norm=0.0,
            y_norm=0.0,
            z_norm=0.0,
            gradient_type="components",
            lower_bound=0.0,
            max_global_iterations=max_iterations,
            initial_beta_ratio=1e-2,
            prctile=100,
            store_sensitivities="ram",
        )

    driver = JointSurveyDriver(joint_params)
    driver.run()

    with Workspace(driver.params.geoh5.h5file):
        output = get_inversion_output(
            driver.params.geoh5.h5file, driver.params.out_group.uid
        )
        output["data"] = np.hstack(orig_data)

        if unittest:
            check_target(output, target_run)


if __name__ == "__main__":
    # Full run
    test_joint_surveys_fwr_run(
        Path("./"),
        n_grid_points=20,
        refinement=(4, 8),
    )
    test_joint_surveys_inv_run(
        Path("./"),
        max_iterations=20,
        unittest=False,
    )
