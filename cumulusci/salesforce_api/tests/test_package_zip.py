from unittest import mock
import base64
import io
import os
import unittest
import zipfile

from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.salesforce_api.package_zip import CreatePackageZipBuilder
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.package_zip import DestructiveChangesZipBuilder
from cumulusci.salesforce_api.package_zip import MetadataPackageZipBuilder
from cumulusci.salesforce_api.package_zip import UninstallPackageZipBuilder
from cumulusci.utils import temporary_dir
from cumulusci.utils import touch


class TestBasePackageZipBuilder:
    def test_as_hash(self):
        builder = BasePackageZipBuilder()
        builder.zf.writestr("1", "1")
        hash1 = builder.as_hash()

        builder = BasePackageZipBuilder()
        builder.zf.writestr("1", "1")
        hash2 = builder.as_hash()

        assert hash2 == hash1

        builder.zf.writestr("2", "2")
        hash3 = builder.as_hash()
        assert hash3 != hash2


class TestMetadataPackageZipBuilder:
    def test_builder(self):
        with temporary_dir() as path:

            # add package.xml
            with open(os.path.join(path, "package.xml"), "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>45.0</version>
</Package>"""
                )

            # add lwc
            lwc_path = os.path.join(path, "lwc")
            os.mkdir(lwc_path)

            # add lwc linting files (not included in zip)
            lwc_ignored_files = [".eslintrc.json", "jsconfig.json"]
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_path, lwc_ignored_file))

            # add lwc component
            lwc_component_path = os.path.join(lwc_path, "myComponent")
            os.mkdir(lwc_component_path)

            # add lwc component files included in zip (in alphabetical order)
            lwc_component_files = [
                {"name": "myComponent.html"},
                {"name": "myComponent.js"},
                {
                    "name": "myComponent.js-meta.xml",
                    "body:": """<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata" fqn="myComponent">
    <apiVersion>45.0</apiVersion>
    <isExposed>false</isExposed>
</LightningComponentBundle>""",
                },
                {"name": "myComponent.svg"},
                {"name": "myComponent.css"},
            ]
            for lwc_component_file in lwc_component_files:
                with open(
                    os.path.join(lwc_component_path, lwc_component_file.get("name")),
                    "w",
                ) as f:
                    if lwc_component_file.get("body") is not None:
                        f.write(lwc_component_file.get("body"))

            # add lwc component files not included in zip
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_component_path, lwc_ignored_file))

            # add lwc component sub-directory and files not included in zip
            lwc_component_test_path = os.path.join(lwc_component_path, "__tests__")
            os.mkdir(lwc_component_test_path)
            touch(os.path.join(lwc_component_test_path, "test.js"))

            # add classes
            classes_path = os.path.join(path, "classes")
            os.mkdir(classes_path)
            class_files = [
                {
                    "name": "MyClass.cls-meta.xml",
                    "body": """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>45.0</apiVersion>
    <status>Active</status>
</ApexClass>
""",
                },
                {"name": "MyClass.cls"},
            ]
            for class_file in class_files:
                with open(os.path.join(classes_path, class_file.get("name")), "w") as f:
                    if class_file.get("body") is not None:
                        f.write(class_file.get("body"))

            # add objects
            objects_path = os.path.join(path, "objects")
            os.mkdir(objects_path)
            object_file_names = ["Account.object", "Contact.object", "CustomObject__c"]
            object_file_names.sort()
            for object_file_name in object_file_names:
                touch(os.path.join(objects_path, object_file_name))

            # add sub-directory of objects (that doesn't really exist)
            objects_sub_path = os.path.join(objects_path, "does-not-exist-in-schema")
            os.mkdir(objects_sub_path)
            touch(os.path.join(objects_sub_path, "some.file"))

            # test
            builder = MetadataPackageZipBuilder(
                path=path,
                options={
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                },
            )

            # make sure result can be read as a zipfile
            result = builder.as_base64()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(result)), "r")
            assert set(zf.namelist()) == {
                "package.xml",
                "lwc/myComponent/myComponent.html",
                "lwc/myComponent/myComponent.js",
                "lwc/myComponent/myComponent.js-meta.xml",
                "lwc/myComponent/myComponent.svg",
                "lwc/myComponent/myComponent.css",
                "classes/MyClass.cls-meta.xml",
                "classes/MyClass.cls",
                "objects/Account.object",
                "objects/Contact.object",
                "objects/CustomObject__c",
                "objects/does-not-exist-in-schema/some.file",
            }

    def test_add_files_to_package(self):
        with temporary_dir() as path:
            expected = []

            # add package.xml
            with open(os.path.join(path, "package.xml"), "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>45.0</version>
</Package>"""
                )
                expected.append("package.xml")

            # add lwc
            lwc_path = os.path.join(path, "lwc")
            rel_lwc_path = "lwc"
            os.mkdir(lwc_path)

            # add lwc linting files (not included in zip)
            lwc_ignored_files = [".eslintrc.json", "jsconfig.json"]
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_path, lwc_ignored_file))

            # add lwc component
            lwc_component_path = os.path.join(lwc_path, "myComponent")
            rel_lwc_component_path = os.path.join(rel_lwc_path, "myComponent")
            os.mkdir(lwc_component_path)

            # add lwc component files included in zip (in alphabetical order)
            lwc_component_files = [
                {"name": "myComponent.html"},
                {"name": "myComponent.js"},
                {
                    "name": "myComponent.js-meta.xml",
                    "body:": """<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata" fqn="myComponent">
    <apiVersion>45.0</apiVersion>
    <isExposed>false</isExposed>
</LightningComponentBundle>""",
                },
                {"name": "myComponent.svg"},
                {"name": "myComponent.css"},
            ]
            for lwc_component_file in lwc_component_files:
                with open(
                    os.path.join(lwc_component_path, lwc_component_file.get("name")),
                    "w",
                ) as f:
                    if lwc_component_file.get("body") is not None:
                        f.write(lwc_component_file.get("body"))
                    expected.append(
                        os.path.join(
                            rel_lwc_component_path, lwc_component_file.get("name")
                        )
                    )

            # add lwc component files not included in zip
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_component_path, lwc_ignored_file))

            # add lwc component sub-directory and files not included in zip
            lwc_component_test_path = os.path.join(lwc_component_path, "__tests__")
            os.mkdir(lwc_component_test_path)
            touch(os.path.join(lwc_component_test_path, "test.js"))

            # add classes
            classes_path = os.path.join(path, "classes")
            rel_classes_path = "classes"
            os.mkdir(classes_path)
            class_files = [
                {
                    "name": "MyClass.cls-meta.xml",
                    "body": """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>45.0</apiVersion>
    <status>Active</status>
</ApexClass>
""",
                },
                {"name": "MyClass.cls"},
            ]
            for class_file in class_files:
                with open(os.path.join(classes_path, class_file.get("name")), "w") as f:
                    if class_file.get("body") is not None:
                        f.write(class_file.get("body"))
                    expected.append(
                        os.path.join(rel_classes_path, class_file.get("name"))
                    )

            # add objects
            objects_path = os.path.join(path, "objects")
            rel_objects_path = "objects"
            os.mkdir(objects_path)
            object_file_names = ["Account.object", "Contact.object", "CustomObject__c"]
            object_file_names.sort()
            for object_file_name in object_file_names:
                with open(os.path.join(objects_path, object_file_name), "w"):
                    expected.append(os.path.join(rel_objects_path, object_file_name))

            # add sub-directory of objects (that doesn't really exist)
            objects_sub_path = os.path.join(objects_path, "does-not-exist-in-schema")
            rel_objects_sub_path = os.path.join(
                rel_objects_path, "does-not-exist-in-schema"
            )
            os.mkdir(objects_sub_path)
            with open(os.path.join(objects_sub_path, "some.file"), "w"):
                expected.append(os.path.join(rel_objects_sub_path, "some.file"))

            # test
            builder = MetadataPackageZipBuilder()

            expected_set = set(expected)
            builder._add_files_to_package(path)
            actual_set = set(builder.zf.namelist())
            assert expected_set == actual_set

    def test_include_directory(self):
        builder = MetadataPackageZipBuilder()

        # include root directory
        assert builder._include_directory([]) is True

        # not include lwc directory
        assert builder._include_directory(["lwc"]) is False

        # include any lwc sub-directory (i.e. lwc component directory)
        assert builder._include_directory(["lwc", "myComponent"]) is True
        assert builder._include_directory(["lwc", "lwc"]) is True

        # not include any sub-*-directory of a lwc sub-directory
        assert builder._include_directory(["lwc", "myComponent", "__tests__"]) is False
        assert (
            builder._include_directory(["lwc", "myComponent", "sub-1", "sub-2"])
            is False
        )
        assert (
            builder._include_directory(
                ["lwc", "myComponent", "sub-1", "sub-2", "sub-3"]
            )
            is False
        )
        assert (
            builder._include_directory(
                ["lwc", "myComponent", "sub-1", "sub-2", "sub-3", "sub-4"]
            )
            is False
        )

        # include any non-lwc directory
        assert builder._include_directory(["not-lwc"]) is True
        assert builder._include_directory(["classes"]) is True
        assert builder._include_directory(["objects"]) is True

        # include any sub_* directory of a non-lwc directory
        assert builder._include_directory(["not-lwc", "sub-1"]) is True
        assert builder._include_directory(["not-lwc", "sub-1", "sub-2"]) is True
        assert (
            builder._include_directory(["not-lwc", "sub-1", "sub-2", "sub-3"]) is True
        )
        assert (
            builder._include_directory(["not-lwc", "sub-1", "sub-2", "sub-3", "sub-4"])
            is True
        )

    def test_include_file(self):
        builder = MetadataPackageZipBuilder()

        lwc_component_directory = ["lwc", "myComponent"]
        non_lwc_component_directories = [
            [],
            ["lwc"],
            ["lwc", "myComponent", "sub-1"],
            ["lwc", "myComponent", "sub-2"],
            ["classes"],
            ["objects", "sub-1"],
            ["objects", "sub-1", "sub-2"],
        ]

        # file endings in lwc component whitelist
        for file_ending in [".js", ".js-meta.xml", ".html", ".css", ".svg"]:
            # lwc_component_directory
            assert (
                builder._include_file(
                    lwc_component_directory, "file_name" + file_ending
                )
                is True
            )

            # non_lwc_component_directories
            for d in non_lwc_component_directories:
                assert builder._include_file(d, "file_name" + file_ending) is True

        # file endings not in lwc component whitelist
        for file_ending in ["", ".json", ".xml", ".cls", ".cls-meta.xml", ".object"]:
            # lwc_component_directory
            assert (
                builder._include_file(
                    lwc_component_directory, "file_name" + file_ending
                )
                is False
            )

            # non_lwc_component_directories
            for d in non_lwc_component_directories:
                assert builder._include_file(d, "file_name" + file_ending) is True

    def test_convert_sfdx(self):
        with temporary_dir() as path:
            with mock.patch("cumulusci.salesforce_api.package_zip.sfdx") as sfdx:
                builder = MetadataPackageZipBuilder()
                with builder._convert_sfdx_format(path, "Test Package"):
                    pass
        sfdx.assert_called_once()


class TestCreatePackageZipBuilder(unittest.TestCase):
    def test_init__missing_name(self):
        with self.assertRaises(ValueError):
            CreatePackageZipBuilder(None, "43.0")

    def test_init__missing_api_version(self):
        with self.assertRaises(ValueError):
            CreatePackageZipBuilder("TestPackage", None)


class TestInstallPackageZipBuilder(unittest.TestCase):
    def test_init__missing_namespace(self):
        with self.assertRaises(ValueError):
            InstallPackageZipBuilder(None, "1.0")

    def test_init__missing_version(self):
        with self.assertRaises(ValueError):
            InstallPackageZipBuilder("testns", None)


class TestDestructiveChangesZipBuilder(unittest.TestCase):
    def test_call(self):
        builder = DestructiveChangesZipBuilder("", "1.0")
        names = builder.zf.namelist()
        self.assertIn("package.xml", names)
        self.assertIn("destructiveChanges.xml", names)


class TestUninstallPackageZipBuilder(unittest.TestCase):
    def test_init__missing_namespace(self):
        with self.assertRaises(ValueError):
            UninstallPackageZipBuilder(None, "1.0")

    def test_call(self):
        builder = UninstallPackageZipBuilder("testns", "1.0")
        self.assertIn("destructiveChanges.xml", builder.zf.namelist())
