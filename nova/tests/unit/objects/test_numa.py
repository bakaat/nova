#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from nova import exception
from nova import objects
from nova.tests.unit.objects import test_objects

fake_obj_numa = objects.NUMATopology(
    cells=[
        objects.NUMACell(
            id=0, cpuset=set([1, 2]), memory=512,
            cpu_usage=2, memory_usage=256,
            mempages=[], pinned_cpus=set([]),
            siblings=[]),
        objects.NUMACell(
            id=1, cpuset=set([3, 4]), memory=512,
            cpu_usage=1, memory_usage=128,
            mempages=[], pinned_cpus=set([]),
            siblings=[])])


class _TestNUMA(object):

    def test_convert_wipe(self):
        d1 = fake_obj_numa._to_dict()
        d2 = objects.NUMATopology.obj_from_primitive(d1)._to_dict()

        self.assertEqual(d1, d2)

    def test_free_cpus(self):
        obj = objects.NUMATopology(cells=[
            objects.NUMACell(
                id=0, cpuset=set([1, 2]), memory=512,
                cpu_usage=2, memory_usage=256,
                pinned_cpus=set([1]), siblings=[],
                mempages=[]),
            objects.NUMACell(
                id=1, cpuset=set([3, 4]), memory=512,
                cpu_usage=1, memory_usage=128,
                pinned_cpus=set([]), siblings=[],
                mempages=[])
            ]
        )
        self.assertEqual(set([2]), obj.cells[0].free_cpus)
        self.assertEqual(set([3, 4]), obj.cells[1].free_cpus)

    def test_pinning_logic(self):
        numacell = objects.NUMACell(id=0, cpuset=set([1, 2, 3, 4]), memory=512,
                                    cpu_usage=2, memory_usage=256,
                                    pinned_cpus=set([1]), siblings=[],
                                    mempages=[])
        numacell.pin_cpus(set([2, 3]))
        self.assertEqual(set([4]), numacell.free_cpus)
        self.assertRaises(exception.CPUPinningInvalid,
                          numacell.pin_cpus, set([1, 4]))
        self.assertRaises(exception.CPUPinningInvalid,
                          numacell.pin_cpus, set([1, 6]))
        self.assertRaises(exception.CPUPinningInvalid,
                          numacell.unpin_cpus, set([1, 4]))
        numacell.unpin_cpus(set([1, 2, 3]))
        self.assertEqual(set([1, 2, 3, 4]), numacell.free_cpus)

    def test_pages_topology_wipe(self):
        pages_topology = objects.NUMAPagesTopology(
            size_kb=2048, total=1024, used=512)

        self.assertEqual(2048, pages_topology.size_kb)
        self.assertEqual(1024, pages_topology.total)
        self.assertEqual(512, pages_topology.used)
        self.assertEqual(512, pages_topology.free)
        self.assertEqual(1048576, pages_topology.free_kb)

    def test_can_fit_hugepages(self):
        cell = objects.NUMACell(
            id=0, cpuset=set([1, 2]), memory=1024,
            siblings=[], pinned_cpus=set([]),
            mempages=[
                objects.NUMAPagesTopology(
                    size_kb=4, total=1548736, used=0),
                objects.NUMAPagesTopology(
                    size_kb=2048, total=513, used=0)])  # 1,002G

        pagesize = 2048

        self.assertTrue(cell.can_fit_hugepages(pagesize, 2 ** 20))
        self.assertFalse(cell.can_fit_hugepages(pagesize, 2 ** 21))
        self.assertFalse(cell.can_fit_hugepages(pagesize, 2 ** 19 + 1))
        self.assertRaises(
            exception.MemoryPageSizeNotSupported,
            cell.can_fit_hugepages, 12345, 2 ** 20)

    def test_default_behavior(self):
        inst_cell = objects.NUMACell()
        self.assertEqual(0, len(inst_cell.obj_get_changes()))

    def test_obj_cell_relationships(self):
        obj = objects.NUMATopology(cells=[objects.NUMACell()])
        rel = objects.NUMATopology.obj_relationships['cells']
        for topo_ver, cell_ver in rel:
            prim = obj.obj_to_primitive(target_version=topo_ver)
            cell = objects.NUMATopology.obj_from_primitive(prim).cells[0]
            self.assertEqual(cell_ver, cell.VERSION)

    def test_numa_pages_equivalent(self):
        pt1 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        pt2 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        self.assertEqual(pt1, pt2)

    def test_numa_pages_not_equivalent(self):
        pt1 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        pt2 = objects.NUMAPagesTopology(size_kb=1024, total=33, used=0)
        self.assertNotEqual(pt1, pt2)

    def test_numa_pages_not_equivalent_missing_a(self):
        pt1 = objects.NUMAPagesTopology(size_kb=1024, used=0)
        pt2 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        self.assertNotEqual(pt1, pt2)

    def test_numa_pages_not_equivalent_missing_b(self):
        pt1 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        pt2 = objects.NUMAPagesTopology(size_kb=1024, used=0)
        self.assertNotEqual(pt1, pt2)

    def test_numa_cell_equivalent(self):
        cell1 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        cell2 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        self.assertEqual(cell1, cell2)

    def test_numa_cell_not_equivalent(self):
        cell1 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        cell2 = objects.NUMACell(id=2, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        self.assertNotEqual(cell1, cell2)

    def test_numa_cell_not_equivalent_missing_a(self):
        cell1 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        cell2 = objects.NUMACell(id=2, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        self.assertNotEqual(cell1, cell2)

    def test_numa_cell_not_equivalent_missing_b(self):
        cell1 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        cell2 = objects.NUMACell(id=2, cpuset=set([1, 2]), memory=32,
                                 pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])])
        self.assertNotEqual(cell1, cell2)

    def test_numa_cell_equivalent_different_pages(self):
        pt1 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        pt2 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        cell1 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])],
                                 mempages=[pt1])
        cell2 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])],
                                 mempages=[pt2])
        self.assertEqual(cell1, cell2)

    def test_numa_cell_not_equivalent_different_pages(self):
        pt1 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=0)
        pt2 = objects.NUMAPagesTopology(size_kb=1024, total=32, used=1)
        cell1 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])],
                                 mempages=[pt1])
        cell2 = objects.NUMACell(id=1, cpuset=set([1, 2]), memory=32,
                                 cpu_usage=10, pinned_cpus=set([3, 4]),
                                 siblings=[set([5, 6])],
                                 mempages=[pt2])
        self.assertNotEqual(cell1, cell2)


class TestNUMA(test_objects._LocalTest,
               _TestNUMA):
    pass


class TestNUMARemote(test_objects._RemoteTest,
                     _TestNUMA):
    pass
