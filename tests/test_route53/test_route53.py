import boto3
from botocore.exceptions import ClientError

import sure  # noqa # pylint: disable=unused-import

import botocore
import pytest

from moto import mock_route53


@mock_route53
def test_create_hosted_zone_boto3():
    conn = boto3.client("route53", region_name="us-east-1")
    response = conn.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )
    firstzone = response["HostedZone"]
    firstzone.should.have.key("Id").match(r"/hostedzone/[A-Z0-9]+")
    firstzone.should.have.key("Name").equal("testdns.aws.com.")
    firstzone.should.have.key("Config").equal({"PrivateZone": False})
    firstzone.should.have.key("ResourceRecordSetCount").equal(0)

    delegation = response["DelegationSet"]
    delegation.should.equal({"NameServers": ["moto.test.com"]})


@mock_route53
def test_list_hosted_zones():
    conn = boto3.client("route53", region_name="us-east-1")

    res = conn.list_hosted_zones()["HostedZones"]
    res.should.have.length_of(0)

    zone1 = conn.create_hosted_zone(
        Name="testdns1.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]
    zone2 = conn.create_hosted_zone(
        Name="testdns2.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]

    res = conn.list_hosted_zones()["HostedZones"]
    res.should.have.length_of(2)

    res.should.contain(zone1)
    res.should.contain(zone2)


@mock_route53
def test_delete_hosted_zone():
    conn = boto3.client("route53", region_name="us-east-1")

    zone1 = conn.create_hosted_zone(
        Name="testdns1.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]
    conn.create_hosted_zone(Name="testdns2.aws.com.", CallerReference=str(hash("foo")))

    conn.delete_hosted_zone(Id=zone1["Id"])

    res = conn.list_hosted_zones()["HostedZones"]
    res.should.have.length_of(1)


@mock_route53
def test_get_unknown_hosted_zone():
    conn = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_hosted_zone(Id="unknown")

    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchHostedZone")
    err["Message"].should.equal("No hosted zone found with ID: unknown")


@mock_route53
def test_list_resource_record_set_unknown_zone():
    conn = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_resource_record_sets(HostedZoneId="abcd")

    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchHostedZone")
    err["Message"].should.equal("No hosted zone found with ID: abcd")


@mock_route53
def test_list_resource_record_set_unknown_type():
    conn = boto3.client("route53", region_name="us-east-1")
    zone = conn.create_hosted_zone(
        Name="testdns1.aws.com.", CallerReference=str(hash("foo"))
    )["HostedZone"]

    with pytest.raises(ClientError) as ex:
        conn.list_resource_record_sets(HostedZoneId=zone["Id"], StartRecordType="A")

    err = ex.value.response["Error"]
    err["Code"].should.equal("400")
    err["Message"].should.equal("Bad Request")


@mock_route53
def test_create_health_check_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "SearchString": "a good response",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]
    check.should.have.key("Id").match("[a-z0-9-]+")
    check.should.have.key("CallerReference")
    check.should.have.key("HealthCheckConfig")
    check["HealthCheckConfig"].should.have.key("IPAddress").equal("10.0.0.25")
    check["HealthCheckConfig"].should.have.key("Port").equal(80)
    check["HealthCheckConfig"].should.have.key("Type").equal("HTTP")
    check["HealthCheckConfig"].should.have.key("ResourcePath").equal("/")
    check["HealthCheckConfig"].should.have.key("FullyQualifiedDomainName").equal(
        "example.com"
    )
    check["HealthCheckConfig"].should.have.key("SearchString").equal("a good response")
    check["HealthCheckConfig"].should.have.key("RequestInterval").equal(10)
    check["HealthCheckConfig"].should.have.key("FailureThreshold").equal(2)
    check.should.have.key("HealthCheckVersion").equal(1)


@mock_route53
def test_list_health_checks_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    conn.list_health_checks()["HealthChecks"].should.have.length_of(0)

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "SearchString": "a good response",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]

    checks = conn.list_health_checks()["HealthChecks"]
    checks.should.have.length_of(1)
    checks.should.contain(check)


@mock_route53
def test_delete_health_checks_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    conn.list_health_checks()["HealthChecks"].should.have.length_of(0)

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "FullyQualifiedDomainName": "example.com",
            "SearchString": "a good response",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]

    conn.delete_health_check(HealthCheckId=check["Id"])

    checks = conn.list_health_checks()["HealthChecks"]
    checks.should.have.length_of(0)


@mock_route53
def test_use_health_check_in_resource_record_set_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    check = conn.create_health_check(
        CallerReference="?",
        HealthCheckConfig={
            "IPAddress": "10.0.0.25",
            "Port": 80,
            "Type": "HTTP",
            "ResourcePath": "/",
            "RequestInterval": 10,
            "FailureThreshold": 2,
        },
    )["HealthCheck"]
    check_id = check["Id"]

    zone = conn.create_hosted_zone(
        Name="testdns.aws.com", CallerReference=str(hash("foo"))
    )
    zone_id = zone["HostedZone"]["Id"]

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "foo.bar.testdns.aws.com",
                        "Type": "A",
                        "HealthCheckId": check_id,
                        "ResourceRecords": [{"Value": "1.2.3.4"}],
                    },
                }
            ]
        },
    )

    record_sets = conn.list_resource_record_sets(HostedZoneId=zone_id)[
        "ResourceRecordSets"
    ]
    record_sets[0]["Name"].should.equal("foo.bar.testdns.aws.com.")
    record_sets[0]["HealthCheckId"].should.equal(check_id)


@mock_route53
def test_hosted_zone_comment_preserved_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    firstzone = conn.create_hosted_zone(
        Name="testdns.aws.com",
        CallerReference=str(hash("foo")),
        HostedZoneConfig={"Comment": "test comment"},
    )
    zone_id = firstzone["HostedZone"]["Id"]

    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    hosted_zone["HostedZone"]["Config"]["Comment"].should.equal("test comment")

    hosted_zones = conn.list_hosted_zones()
    hosted_zones["HostedZones"][0]["Config"]["Comment"].should.equal("test comment")


@mock_route53
def test_deleting_weighted_route_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    zone = conn.create_hosted_zone(
        Name="testdns.aws.com", CallerReference=str(hash("foo"))
    )
    zone_id = zone["HostedZone"]["Id"]

    for identifier in ["success-test-foo", "success-test-bar"]:
        conn.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "cname.testdns.aws.com",
                            "Type": "CNAME",
                            "SetIdentifier": identifier,
                            "Weight": 50,
                        },
                    }
                ]
            },
        )

    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    cnames.should.have.length_of(2)

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": "cname.testdns.aws.com",
                        "Type": "CNAME",
                        "SetIdentifier": "success-test-foo",
                    },
                }
            ]
        },
    )

    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    cnames.should.have.length_of(1)
    cnames[0]["Name"].should.equal("cname.testdns.aws.com.")
    cnames[0]["SetIdentifier"].should.equal("success-test-bar")


@mock_route53
def test_deleting_latency_route_boto3():
    conn = boto3.client("route53", region_name="us-east-1")

    zone = conn.create_hosted_zone(
        Name="testdns.aws.com", CallerReference=str(hash("foo"))
    )
    zone_id = zone["HostedZone"]["Id"]

    for _id, region in [
        ("success-test-foo", "us-west-2"),
        ("success-test-bar", "us-west-1"),
    ]:
        conn.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch={
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": "cname.testdns.aws.com",
                            "Type": "CNAME",
                            "SetIdentifier": _id,
                            "Region": region,
                            "ResourceRecords": [{"Value": "example.com"}],
                        },
                    }
                ]
            },
        )

    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    cnames.should.have.length_of(2)
    foo_cname = [
        cname for cname in cnames if cname["SetIdentifier"] == "success-test-foo"
    ][0]
    foo_cname["Region"].should.equal("us-west-2")

    conn.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": "cname.testdns.aws.com",
                        "Type": "CNAME",
                        "SetIdentifier": "success-test-foo",
                    },
                }
            ]
        },
    )
    cnames = conn.list_resource_record_sets(
        HostedZoneId=zone_id, StartRecordName="cname", StartRecordType="CNAME"
    )["ResourceRecordSets"]
    cnames.should.have.length_of(1)
    cnames[0]["SetIdentifier"].should.equal("success-test-bar")
    cnames[0]["Region"].should.equal("us-west-1")


@mock_route53
def test_hosted_zone_private_zone_preserved_boto3():
    conn = boto3.client("route53", region_name="us-east-1")
    # TODO: actually create_hosted_zone statements with PrivateZone=True, but without
    # a _valid_ vpc-id should fail.
    firstzone = conn.create_hosted_zone(
        Name="testdns.aws.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="Test"),
    )

    zone_id = firstzone["HostedZone"]["Id"].split("/")[-1]

    hosted_zone = conn.get_hosted_zone(Id=zone_id)
    hosted_zone["HostedZone"]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones()
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)

    hosted_zones = conn.list_hosted_zones_by_name(DNSName="testdns.aws.com.")
    len(hosted_zones["HostedZones"]).should.equal(1)
    hosted_zones["HostedZones"][0]["Config"]["PrivateZone"].should.equal(True)


@mock_route53
def test_list_or_change_tags_for_resource_request():
    conn = boto3.client("route53", region_name="us-east-1")
    health_check = conn.create_health_check(
        CallerReference="foobar",
        HealthCheckConfig={
            "IPAddress": "192.0.2.44",
            "Port": 123,
            "Type": "HTTP",
            "ResourcePath": "/",
            "RequestInterval": 30,
            "FailureThreshold": 123,
            "HealthThreshold": 123,
        },
    )
    healthcheck_id = health_check["HealthCheck"]["Id"]

    # confirm this works for resources with zero tags
    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    response["ResourceTagSet"]["Tags"].should.be.empty

    tag1 = {"Key": "Deploy", "Value": "True"}
    tag2 = {"Key": "Name", "Value": "UnitTest"}

    # Test adding a tag for a resource id
    conn.change_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id, AddTags=[tag1, tag2]
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    response.should.contain("ResourceTagSet")

    # Validate that each key was added
    response["ResourceTagSet"]["Tags"].should.contain(tag1)
    response["ResourceTagSet"]["Tags"].should.contain(tag2)

    len(response["ResourceTagSet"]["Tags"]).should.equal(2)

    # Try to remove the tags
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag1["Key"]],
    )

    # Check to make sure that the response has the 'ResourceTagSet' key
    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    response.should.contain("ResourceTagSet")
    response["ResourceTagSet"]["Tags"].should_not.contain(tag1)
    response["ResourceTagSet"]["Tags"].should.contain(tag2)

    # Remove the second tag
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag2["Key"]],
    )

    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    response["ResourceTagSet"]["Tags"].should_not.contain(tag2)

    # Re-add the tags
    conn.change_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id, AddTags=[tag1, tag2]
    )

    # Remove both
    conn.change_tags_for_resource(
        ResourceType="healthcheck",
        ResourceId=healthcheck_id,
        RemoveTagKeys=[tag1["Key"], tag2["Key"]],
    )

    response = conn.list_tags_for_resource(
        ResourceType="healthcheck", ResourceId=healthcheck_id
    )
    response["ResourceTagSet"]["Tags"].should.be.empty


@mock_route53
def test_list_hosted_zones_by_name():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test com"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test org"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test org 2"),
    )

    # test lookup
    zones = conn.list_hosted_zones_by_name(DNSName="test.b.com.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("test.b.com.")
    zones = conn.list_hosted_zones_by_name(DNSName="test.a.org.")
    len(zones["HostedZones"]).should.equal(2)
    zones["HostedZones"][0]["Name"].should.equal("test.a.org.")
    zones["HostedZones"][1]["Name"].should.equal("test.a.org.")

    # test sort order
    zones = conn.list_hosted_zones_by_name()
    len(zones["HostedZones"]).should.equal(3)
    zones["HostedZones"][0]["Name"].should.equal("test.b.com.")
    zones["HostedZones"][1]["Name"].should.equal("test.a.org.")
    zones["HostedZones"][2]["Name"].should.equal("test.a.org.")


@mock_route53
def test_list_hosted_zones_by_dns_name():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="test.b.com.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test com"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test org"),
    )
    conn.create_hosted_zone(
        Name="test.a.org.",
        CallerReference=str(hash("bar")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="test org 2"),
    )
    conn.create_hosted_zone(
        Name="my.test.net.",
        CallerReference=str(hash("baz")),
        HostedZoneConfig=dict(PrivateZone=False, Comment="test net"),
    )

    # test lookup
    zones = conn.list_hosted_zones_by_name(DNSName="test.b.com.")
    len(zones["HostedZones"]).should.equal(1)
    zones["DNSName"].should.equal("test.b.com.")
    zones = conn.list_hosted_zones_by_name(DNSName="test.a.org.")
    len(zones["HostedZones"]).should.equal(2)
    zones["DNSName"].should.equal("test.a.org.")
    zones["DNSName"].should.equal("test.a.org.")
    zones = conn.list_hosted_zones_by_name(DNSName="my.test.net.")
    len(zones["HostedZones"]).should.equal(1)
    zones["DNSName"].should.equal("my.test.net.")
    zones = conn.list_hosted_zones_by_name(DNSName="my.test.net")
    len(zones["HostedZones"]).should.equal(1)
    zones["DNSName"].should.equal("my.test.net.")

    # test sort order
    zones = conn.list_hosted_zones_by_name()
    len(zones["HostedZones"]).should.equal(4)
    zones["HostedZones"][0]["Name"].should.equal("test.b.com.")
    zones["HostedZones"][1]["Name"].should.equal("my.test.net.")
    zones["HostedZones"][2]["Name"].should.equal("test.a.org.")
    zones["HostedZones"][3]["Name"].should.equal("test.a.org.")


@mock_route53
def test_change_resource_record_sets_crud_valid():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create A Record.
    a_record_endpoint_payload = {
        "Comment": "Create A record prod.redis.db",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=a_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)
    a_record_detail = response["ResourceRecordSets"][0]
    a_record_detail["Name"].should.equal("prod.redis.db.")
    a_record_detail["Type"].should.equal("A")
    a_record_detail["TTL"].should.equal(10)
    a_record_detail["ResourceRecords"].should.equal([{"Value": "127.0.0.1"}])

    # Update A Record.
    cname_record_endpoint_payload = {
        "Comment": "Update A record prod.redis.db",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 60,
                    "ResourceRecords": [{"Value": "192.168.1.1"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=cname_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)
    cname_record_detail = response["ResourceRecordSets"][0]
    cname_record_detail["Name"].should.equal("prod.redis.db.")
    cname_record_detail["Type"].should.equal("A")
    cname_record_detail["TTL"].should.equal(60)
    cname_record_detail["ResourceRecords"].should.equal([{"Value": "192.168.1.1"}])

    # Update to add Alias.
    cname_alias_record_endpoint_payload = {
        "Comment": "Update to Alias prod.redis.db",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "A",
                    "TTL": 60,
                    "AliasTarget": {
                        "HostedZoneId": hosted_zone_id,
                        "DNSName": "prod.redis.alias.",
                        "EvaluateTargetHealth": False,
                    },
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=cname_alias_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    cname_alias_record_detail = response["ResourceRecordSets"][0]
    cname_alias_record_detail["Name"].should.equal("prod.redis.db.")
    cname_alias_record_detail["Type"].should.equal("A")
    cname_alias_record_detail["TTL"].should.equal(60)
    cname_alias_record_detail["AliasTarget"].should.equal(
        {
            "HostedZoneId": hosted_zone_id,
            "DNSName": "prod.redis.alias.",
            "EvaluateTargetHealth": False,
        }
    )
    cname_alias_record_detail.should_not.contain("ResourceRecords")

    # Delete record with wrong type.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {"Name": "prod.redis.db", "Type": "CNAME"},
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)

    # Delete record.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {"Name": "prod.redis.db", "Type": "A"},
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(0)


@mock_route53
def test_change_resource_record_sets_crud_valid_with_special_xml_chars():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create TXT Record.
    txt_record_endpoint_payload = {
        "Comment": "Create TXT record prod.redis.db",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "TXT",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "SomeInitialValue"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=txt_record_endpoint_payload
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)
    a_record_detail = response["ResourceRecordSets"][0]
    a_record_detail["Name"].should.equal("prod.redis.db.")
    a_record_detail["Type"].should.equal("TXT")
    a_record_detail["TTL"].should.equal(10)
    a_record_detail["ResourceRecords"].should.equal([{"Value": "SomeInitialValue"}])

    # Update TXT Record with XML Special Character &.
    txt_record_with_special_char_endpoint_payload = {
        "Comment": "Update TXT record prod.redis.db",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.redis.db.",
                    "Type": "TXT",
                    "TTL": 60,
                    "ResourceRecords": [{"Value": "SomeInitialValue&NewValue"}],
                },
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch=txt_record_with_special_char_endpoint_payload,
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(1)
    cname_record_detail = response["ResourceRecordSets"][0]
    cname_record_detail["Name"].should.equal("prod.redis.db.")
    cname_record_detail["Type"].should.equal("TXT")
    cname_record_detail["TTL"].should.equal(60)
    cname_record_detail["ResourceRecords"].should.equal(
        [{"Value": "SomeInitialValue&NewValue"}]
    )

    # Delete record.
    delete_payload = {
        "Comment": "delete prod.redis.db",
        "Changes": [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {"Name": "prod.redis.db", "Type": "TXT"},
            }
        ],
    }
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=delete_payload
    )
    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(0)


@mock_route53
def test_change_weighted_resource_record_sets():
    conn = boto3.client("route53", region_name="us-east-2")
    conn.create_hosted_zone(
        Name="test.vpc.internal.", CallerReference=str(hash("test"))
    )

    zones = conn.list_hosted_zones_by_name(DNSName="test.vpc.internal.")

    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create 2 weighted records
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "test.vpc.internal",
                        "Type": "A",
                        "SetIdentifier": "test1",
                        "Weight": 50,
                        "AliasTarget": {
                            "HostedZoneId": "Z3AADJGX6KTTL2",
                            "DNSName": "internal-test1lb-447688172.us-east-2.elb.amazonaws.com.",
                            "EvaluateTargetHealth": True,
                        },
                    },
                },
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "test.vpc.internal",
                        "Type": "A",
                        "SetIdentifier": "test2",
                        "Weight": 50,
                        "AliasTarget": {
                            "HostedZoneId": "Z3AADJGX6KTTL2",
                            "DNSName": "internal-testlb2-1116641781.us-east-2.elb.amazonaws.com.",
                            "EvaluateTargetHealth": True,
                        },
                    },
                },
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    record = response["ResourceRecordSets"][0]
    # Update the first record to have a weight of 90
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record["Name"],
                        "Type": record["Type"],
                        "SetIdentifier": record["SetIdentifier"],
                        "Weight": 90,
                        "AliasTarget": {
                            "HostedZoneId": record["AliasTarget"]["HostedZoneId"],
                            "DNSName": record["AliasTarget"]["DNSName"],
                            "EvaluateTargetHealth": record["AliasTarget"][
                                "EvaluateTargetHealth"
                            ],
                        },
                    },
                }
            ]
        },
    )

    record = response["ResourceRecordSets"][1]
    # Update the second record to have a weight of 10
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record["Name"],
                        "Type": record["Type"],
                        "SetIdentifier": record["SetIdentifier"],
                        "Weight": 10,
                        "AliasTarget": {
                            "HostedZoneId": record["AliasTarget"]["HostedZoneId"],
                            "DNSName": record["AliasTarget"]["DNSName"],
                            "EvaluateTargetHealth": record["AliasTarget"][
                                "EvaluateTargetHealth"
                            ],
                        },
                    },
                }
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    for record in response["ResourceRecordSets"]:
        if record["SetIdentifier"] == "test1":
            record["Weight"].should.equal(90)
        if record["SetIdentifier"] == "test2":
            record["Weight"].should.equal(10)


@mock_route53
def test_failover_record_sets():
    conn = boto3.client("route53", region_name="us-east-2")
    conn.create_hosted_zone(Name="test.zone.", CallerReference=str(hash("test")))
    zones = conn.list_hosted_zones_by_name(DNSName="test.zone.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create geolocation record
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "failover.test.zone.",
                        "Type": "A",
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.1"}],
                        "Failover": "PRIMARY",
                    },
                }
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    record = response["ResourceRecordSets"][0]
    record["Failover"].should.equal("PRIMARY")


@mock_route53
def test_geolocation_record_sets():
    conn = boto3.client("route53", region_name="us-east-2")
    conn.create_hosted_zone(Name="test.zone.", CallerReference=str(hash("test")))
    zones = conn.list_hosted_zones_by_name(DNSName="test.zone.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Create geolocation record
    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "georecord1.test.zone.",
                        "Type": "A",
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.1"}],
                        "GeoLocation": {"ContinentCode": "EU"},
                    },
                },
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": "georecord2.test.zone.",
                        "Type": "A",
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.2"}],
                        "GeoLocation": {"CountryCode": "US", "SubdivisionCode": "NY"},
                    },
                },
            ]
        },
    )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    rrs = response["ResourceRecordSets"]
    rrs[0]["GeoLocation"].should.equal({"ContinentCode": "EU"})
    rrs[1]["GeoLocation"].should.equal({"CountryCode": "US", "SubdivisionCode": "NY"})


@mock_route53
def test_change_resource_record_invalid():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    invalid_a_record_payload = {
        "Comment": "this should fail",
        "Changes": [
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "prod.scooby.doo",
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }

    with pytest.raises(botocore.exceptions.ClientError):
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=invalid_a_record_payload
        )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(0)

    invalid_cname_record_payload = {
        "Comment": "this should also fail",
        "Changes": [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "prod.scooby.doo",
                    "Type": "CNAME",
                    "TTL": 10,
                    "ResourceRecords": [{"Value": "127.0.0.1"}],
                },
            }
        ],
    }

    with pytest.raises(botocore.exceptions.ClientError):
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=invalid_cname_record_payload
        )

    response = conn.list_resource_record_sets(HostedZoneId=hosted_zone_id)
    len(response["ResourceRecordSets"]).should.equal(0)


@mock_route53
def test_list_resource_record_sets_name_type_filters():
    conn = boto3.client("route53", region_name="us-east-1")
    create_hosted_zone_response = conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )
    hosted_zone_id = create_hosted_zone_response["HostedZone"]["Id"]

    def create_resource_record_set(rec_type, rec_name):
        payload = {
            "Comment": "create {} record {}".format(rec_type, rec_name),
            "Changes": [
                {
                    "Action": "CREATE",
                    "ResourceRecordSet": {
                        "Name": rec_name,
                        "Type": rec_type,
                        "TTL": 10,
                        "ResourceRecords": [{"Value": "127.0.0.1"}],
                    },
                }
            ],
        }
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=payload
        )

    # record_type, record_name
    all_records = [
        ("A", "a.a.db."),
        ("A", "a.b.db."),
        ("A", "b.b.db."),
        ("CNAME", "b.b.db."),
        ("CNAME", "b.c.db."),
        ("CNAME", "c.c.db."),
    ]
    for record_type, record_name in all_records:
        create_resource_record_set(record_type, record_name)

    start_with = 2
    response = conn.list_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        StartRecordType=all_records[start_with][0],
        StartRecordName=all_records[start_with][1],
    )

    response["IsTruncated"].should.equal(False)

    returned_records = [
        (record["Type"], record["Name"]) for record in response["ResourceRecordSets"]
    ]
    len(returned_records).should.equal(len(all_records) - start_with)
    for desired_record in all_records[start_with:]:
        returned_records.should.contain(desired_record)


@mock_route53
def test_get_change():
    conn = boto3.client("route53", region_name="us-east-2")

    change_id = "123456"
    response = conn.get_change(Id=change_id)

    response["ChangeInfo"]["Id"].should.equal(change_id)
    response["ChangeInfo"]["Status"].should.equal("INSYNC")


@mock_route53
def test_change_resource_record_sets_records_limit():
    conn = boto3.client("route53", region_name="us-east-1")
    conn.create_hosted_zone(
        Name="db.",
        CallerReference=str(hash("foo")),
        HostedZoneConfig=dict(PrivateZone=True, Comment="db"),
    )

    zones = conn.list_hosted_zones_by_name(DNSName="db.")
    len(zones["HostedZones"]).should.equal(1)
    zones["HostedZones"][0]["Name"].should.equal("db.")
    hosted_zone_id = zones["HostedZones"][0]["Id"]

    # Changes creating exactly 1,000 resource records.
    changes = []
    for ci in range(4):
        resourcerecords = []
        for rri in range(250):
            resourcerecords.append({"Value": "127.0.0.%d" % (rri)})
        changes.append(
            {
                "Action": "CREATE",
                "ResourceRecordSet": {
                    "Name": "foo%d.db." % (ci),
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": resourcerecords,
                },
            }
        )
    create_1000_resource_records_payload = {
        "Comment": "Create four records with 250 resource records each",
        "Changes": changes,
    }

    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=create_1000_resource_records_payload
    )

    # Changes creating over 1,000 resource records.
    too_many_changes = create_1000_resource_records_payload["Changes"].copy()
    too_many_changes.append(
        {
            "Action": "CREATE",
            "ResourceRecordSet": {
                "Name": "toomany.db.",
                "Type": "A",
                "TTL": 10,
                "ResourceRecords": [{"Value": "127.0.0.1"}],
            },
        }
    )

    create_1001_resource_records_payload = {
        "Comment": "Create four records with 250 resource records each, plus one more",
        "Changes": too_many_changes,
    }

    with pytest.raises(ClientError) as exc:
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch=create_1001_resource_records_payload,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidChangeBatch")

    # Changes upserting exactly 500 resource records.
    changes = []
    for ci in range(2):
        resourcerecords = []
        for rri in range(250):
            resourcerecords.append({"Value": "127.0.0.%d" % (rri)})
        changes.append(
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": "foo%d.db." % (ci),
                    "Type": "A",
                    "TTL": 10,
                    "ResourceRecords": resourcerecords,
                },
            }
        )
    upsert_500_resource_records_payload = {
        "Comment": "Upsert two records with 250 resource records each",
        "Changes": changes,
    }

    conn.change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=upsert_500_resource_records_payload
    )

    # Changes upserting over 1,000 resource records.
    too_many_changes = upsert_500_resource_records_payload["Changes"].copy()
    too_many_changes.append(
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "toomany.db.",
                "Type": "A",
                "TTL": 10,
                "ResourceRecords": [{"Value": "127.0.0.1"}],
            },
        }
    )

    upsert_501_resource_records_payload = {
        "Comment": "Upsert two records with 250 resource records each, plus one more",
        "Changes": too_many_changes,
    }

    with pytest.raises(ClientError) as exc:
        conn.change_resource_record_sets(
            HostedZoneId=hosted_zone_id, ChangeBatch=upsert_501_resource_records_payload
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidChangeBatch")
    err["Message"].should.equal("Number of records limit of 1000 exceeded.")
