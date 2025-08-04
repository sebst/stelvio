from pathlib import Path

import pulumi
import pytest
from pulumi.runtime import set_mocks

from stelvio.aws.api_gateway import Api
from stelvio.component import ComponentRegistry
from stelvio.config import AwsConfig
from stelvio.context import AppContext, _ContextStore
from stelvio.dns import Dns, Record, DnsProviderNotConfiguredError

from ..pulumi_mocks import PulumiTestMocks

# Test prefix - matching the pattern from test_api.py
TP = "test-test-"


class CloudflarePulumiResourceAdapter(Record):
    """Mock adapter that mimics the CloudflarePulumiResourceAdapter"""

    @property
    def name(self):
        return self.pulumi_resource.name

    @property
    def type(self):
        return self.pulumi_resource.type

    @property
    def value(self):
        return self.pulumi_resource.content


class MockDns(Dns):
    """Mock DNS provider that mimics CloudflareDns interface"""

    def __init__(self):
        self.zone_id = "test-zone-id"
        self.created_records = []

    def create_record(
        self, resource_name: str, name: str, record_type: str, value: str, ttl: int = 1
    ) -> Record:
        """Create a mock DNS record following CloudflareDns pattern"""
        import pulumi_cloudflare

        record = pulumi_cloudflare.Record(
            resource_name,
            zone_id=self.zone_id,
            name=name,
            type=record_type,
            content=value,
            ttl=ttl,
        )
        self.created_records.append((resource_name, name, record_type, value, ttl))
        return CloudflarePulumiResourceAdapter(record)

    def create_caa_record(
        self, resource_name: str, name: str, record_type: str, content: str, ttl: int = 1
    ) -> Record:
        """Create a mock CAA DNS record following CloudflareDns pattern"""
        import pulumi_cloudflare

        validation_record = pulumi_cloudflare.Record(
            resource_name,
            zone_id=self.zone_id,
            name=name,
            type=record_type,
            content=content,
            ttl=ttl,
        )
        self.created_records.append((resource_name, name, record_type, content, ttl))
        return CloudflarePulumiResourceAdapter(validation_record)


def delete_files(directory: Path, filename: str):
    directory_path = directory
    for file_path in directory_path.rglob(filename):
        file_path.unlink()


@pytest.fixture
def mock_dns():
    return MockDns()


@pytest.fixture(autouse=True)
def project_cwd(monkeypatch, pytestconfig):
    rootpath = pytestconfig.rootpath
    test_project_dir = rootpath / "tests" / "aws" / "sample_test_project"
    monkeypatch.chdir(test_project_dir)
    yield test_project_dir
    delete_files(test_project_dir, "stlv_resources.py")


@pytest.fixture
def app_context_with_dns(mock_dns):
    """App context with DNS provider configured"""
    _ContextStore.clear()
    _ContextStore.set(
        AppContext(
            name="test",
            env="test",
            aws=AwsConfig(profile="default", region="us-east-1"),
            dns=mock_dns,
        )
    )
    yield mock_dns
    _ContextStore.clear()


@pytest.fixture
def pulumi_mocks():
    mocks = PulumiTestMocks()
    set_mocks(mocks)
    return mocks


@pytest.fixture
def component_registry():
    ComponentRegistry._instances.clear()
    ComponentRegistry._registered_names.clear()
    yield ComponentRegistry
    ComponentRegistry._instances.clear()
    ComponentRegistry._registered_names.clear()


@pulumi.runtime.test
def test_api_without_custom_domain(pulumi_mocks, app_context_with_dns, component_registry):
    """Test that API without custom domain works as before"""
    # Arrange
    api = Api("test-api-no-domain")
    api.route("GET", "/users", "functions/simple.handler")

    # Act
    _ = api.resources

    # Assert
    def check_resources(_):
        # Verify no custom domain resources were created
        assert len(pulumi_mocks.created_certificates()) == 0
        assert len(pulumi_mocks.created_domain_names()) == 0
        assert len(pulumi_mocks.created_base_path_mappings()) == 0

        # Verify normal API resources were created
        assert len(pulumi_mocks.created_rest_apis()) == 1
        assert len(pulumi_mocks.created_stages()) == 1

    api.resources.stage.id.apply(check_resources)


def test_api_custom_domain_validation_errors(app_context_with_dns, component_registry):
    """Test validation errors for custom domain configuration"""
    # Test non-string domain name - this should fail in __init__ before resources are created
    with pytest.raises(TypeError, match="Domain name must be a string"):  # noqa: PT012
        api = Api("test-api-1", domain_name=123)
        _ = api.resources

    # Test empty domain name - this should fail in __init__ before resources are created
    with pytest.raises(ValueError, match="Domain name cannot be empty"):  # noqa: PT012
        api = Api("test-api-2", domain_name="")
        _ = api.resources


@pulumi.runtime.test
def test_api_custom_domain_with_custom_domain(
    pulumi_mocks, app_context_with_dns, component_registry
):
    """Test that API with custom domain works as expected"""
    # Arrange
    mock_dns = app_context_with_dns
    api = Api("test-api-1", domain_name="api.example.com")
    api.route("GET", "/users", "functions/simple.handler")

    # Act
    _ = api.resources

    # Assert
    def check_resources(_):
        # Verify custom domain resources were created
        assert len(pulumi_mocks.created_certificates()) == 1
        assert len(pulumi_mocks.created_domain_names()) == 1

        # Verify normal API resources were created
        assert len(pulumi_mocks.created_rest_apis()) == 1
        assert len(pulumi_mocks.created_stages()) == 1

        # Verify DNS records were created via mock DNS
        assert len(mock_dns.created_records) >= 2, (
            "Should have at least 2 DNS records (validation + API domain)"
        )

        # Verify that we have both types of records by checking resource names
        record_names = [r[0] for r in mock_dns.created_records]
        validation_records = [name for name in record_names if "validation-record" in name]
        api_records = [name for name in record_names if "custom-domain-record" in name]

        assert len(validation_records) >= 1, (
            "DNS validation record should be created for ACM certificate"
        )
        assert len(api_records) >= 1, "API domain DNS record should be created"

    api.resources.stage.id.apply(check_resources)


def test_api_custom_domain_without_dns_provider(component_registry):
    """Test that API with custom domain but no DNS provider raises error"""
    # Arrange - context without DNS provider
    _ContextStore.clear()
    _ContextStore.set(
        AppContext(
            name="test",
            env="test",
            aws=AwsConfig(profile="default", region="us-east-1"),
            dns=None,  # No DNS provider
        )
    )

    api = Api("test-api-3", domain_name="api.example.com")
    api.route("GET", "/users", "functions/simple.handler")

    # Act & Assert - This should fail when trying to access context().dns
    with pytest.raises(DnsProviderNotConfiguredError):
        _ = api.resources

    _ContextStore.clear()
