#!/usr/bin/env python3

import argparse
import os
import yaml  # library: pyyaml
import sys


from junit_xml import TestSuite, TestCase  # library: junit-xml
from yaml import SafeLoader


def parse_args():
    """
    Parse arguments provided to argparse from CLI

    :return : dictionary of parsed arguments
    """
    parser = argparse.ArgumentParser(description="YAML to junit file")
    parser.add_argument('-c', '--config', required=True,
                        help="path to YAML config file")
    parser.add_argument('-o', '--output', required=True,
                        help="path to output junit file")
    return parser.parse_args()


def parse_config(conf):
    """
    Parse provided YAML configuration file

    Example of YAML config:
    # tests
    test_suite:
      - name: 'my_test'
        class_name: 'my_class'
        time: 0
        status: 'passed'
      - name: my_test2
        class_name: my_class
        time: 0
        status: 'failed'
        reason: ''

    :param conf: Path to configuration file

    :return config: Dictionary of loaded configuration
    """
    if not os.path.exists(conf):
        print(f"Config file '{conf}' does not exist")
        sys.exit(1)
    try:
        with open(conf) as f:
            config = yaml.load(f, Loader=SafeLoader)
    except yaml.YAMLError:
        print('Failed to parse YAML file, exiting')
        raise
    print(f"Config '{conf}' was loaded successfully")
    return config


def parse_test_suite(dict_obj):
    test_cases = list()
    try:
        tests = dict_obj['test_suite']
    except KeyError as e:
        print(f"Key {e} is required and not present in config")
        sys.exit(1)
    for test in tests:
        try:
            test_name = test['name']
            test_class = test['class_name']
            test_time = test['time']
            test_status = test['status']
            test_reason = test['reason'] if test['status'] == 'failed' else ''
        except KeyError as e:
            print(f"Key {e} is required and not present in {test}")
            sys.exit(1)
        test_case = TestCase(name=test_name,
                             classname=test_class,
                             elapsed_sec=test_time)
        if test_status == 'failed':
            test_case.add_failure_info(output=test_reason,
                                       failure_type='testtools.testresult.real._StringException')
        test_cases.append(test_case)
    test_suite = TestSuite("my test_suite", test_cases)
    return test_suite


def write_test_suite_file(ts, out):
    with open(out, 'w') as f:
        TestSuite.to_file(f, [ts], prettyprint=False)
    print(f"Generated file at '{out}'")


def main():
    # Supress SSL insecure warning
    args = parse_args()
    config = parse_config(args.config)
    output = args.output
    test_suite = parse_test_suite(config)
    write_test_suite_file(test_suite, output)


if __name__ == '__main__':
    main()
