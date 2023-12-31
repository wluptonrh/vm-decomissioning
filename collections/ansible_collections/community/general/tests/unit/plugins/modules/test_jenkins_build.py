# Copyright (c) Ansible project
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible_collections.community.general.tests.unit.compat import unittest
from ansible_collections.community.general.tests.unit.compat.mock import patch
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from ansible_collections.community.general.plugins.modules import jenkins_build

import json


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""
    pass


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""
    pass


def exit_json(*args, **kwargs):
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class jenkins:
    class JenkinsException(Exception):
        pass

    class NotFoundException(JenkinsException):
        pass


class JenkinsBuildMock():
    def get_build_status(self):
        try:
            instance = JenkinsMock()
            response = JenkinsMock.get_build_info(instance, 'host-delete', 1234)
            return response
        except jenkins.JenkinsException as e:
            response = {}
            response["result"] = "ABSENT"
            return response
        except Exception as e:
            fail_json(msg='Unable to fetch build information, {0}'.format(e))


class JenkinsMock():

    def get_job_info(self, name):
        return {
            "nextBuildNumber": 1234
        }

    def get_build_info(self, name, build_number):
        if name == "host-delete":
            raise jenkins.JenkinsException("job {0} number {1} does not exist".format(name, build_number))
        elif name == "create-detached":
            return {
                "building": True,
                "result": None
            }
        return {
            "building": True,
            "result": "SUCCESS"
        }

    def build_job(self, *args):
        return None

    def delete_build(self, name, build_number):
        return None

    def stop_build(self, name, build_number):
        return None


class JenkinsMockIdempotent():

    def get_job_info(self, name):
        return {
            "nextBuildNumber": 1235
        }

    def get_build_info(self, name, build_number):
        return {
            "building": False,
            "result": "ABORTED"
        }

    def build_job(self, *args):
        return None

    def delete_build(self, name, build_number):
        raise jenkins.NotFoundException("job {0} number {1} does not exist".format(name, build_number))

    def stop_build(self, name, build_number):
        return None


class TestJenkinsBuild(unittest.TestCase):

    def setUp(self):
        self.mock_module_helper = patch.multiple(basic.AnsibleModule,
                                                 exit_json=exit_json,
                                                 fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    def test_module_fail_when_required_args_missing(self, test_deps):
        test_deps.return_value = None
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            jenkins_build.main()

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    def test_module_fail_when_missing_build_number(self, test_deps):
        test_deps.return_value = None
        with self.assertRaises(AnsibleFailJson):
            set_module_args({
                "name": "required-if",
                "state": "stopped"
            })
            jenkins_build.main()

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    def test_module_create_build(self, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMock()

        with self.assertRaises(AnsibleExitJson):
            set_module_args({
                "name": "host-check",
                "user": "abc",
                "token": "xyz"
            })
            jenkins_build.main()

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    def test_module_stop_build(self, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMock()

        with self.assertRaises(AnsibleExitJson) as return_json:
            set_module_args({
                "name": "host-check",
                "build_number": "1234",
                "state": "stopped",
                "user": "abc",
                "token": "xyz"
            })
            jenkins_build.main()

        self.assertTrue(return_json.exception.args[0]['changed'])

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    def test_module_stop_build_again(self, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMockIdempotent()

        with self.assertRaises(AnsibleExitJson) as return_json:
            set_module_args({
                "name": "host-check",
                "build_number": "1234",
                "state": "stopped",
                "user": "abc",
                "password": "xyz"
            })
            jenkins_build.main()

        self.assertFalse(return_json.exception.args[0]['changed'])

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_build_status')
    def test_module_delete_build(self, build_status, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMock()
        build_status.return_value = JenkinsBuildMock().get_build_status()

        with self.assertRaises(AnsibleExitJson):
            set_module_args({
                "name": "host-delete",
                "build_number": "1234",
                "state": "absent",
                "user": "abc",
                "token": "xyz"
            })
            jenkins_build.main()

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    def test_module_delete_build_again(self, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMockIdempotent()

        with self.assertRaises(AnsibleFailJson):
            set_module_args({
                "name": "host-delete",
                "build_number": "1234",
                "state": "absent",
                "user": "abc",
                "token": "xyz"
            })
            jenkins_build.main()

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_build_status')
    def test_module_create_build_without_detach(self, build_status, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMock()
        build_status.return_value = JenkinsBuildMock().get_build_status()

        with self.assertRaises(AnsibleExitJson) as return_json:
            set_module_args({
                "name": "create-detached",
                "user": "abc",
                "token": "xyz"
            })
            jenkins_build.main()

        self.assertFalse(return_json.exception.args[0]['changed'])

    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.test_dependencies')
    @patch('ansible_collections.community.general.plugins.modules.jenkins_build.JenkinsBuild.get_jenkins_connection')
    def test_module_create_build_detached(self, jenkins_connection, test_deps):
        test_deps.return_value = None
        jenkins_connection.return_value = JenkinsMock()

        with self.assertRaises(AnsibleExitJson) as return_json:
            set_module_args({
                "name": "create-detached",
                "user": "abc",
                "token": "xyz",
                "detach": True
            })
            jenkins_build.main()

        self.assertTrue(return_json.exception.args[0]['changed'])
