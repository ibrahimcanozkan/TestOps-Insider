#!/usr/bin/env python3
import subprocess
import time
import argparse
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
K8S_DIR = PROJECT_ROOT / "k8s"


def run_cmd(cmd, capture=False):
    """Run shell command."""
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    subprocess.run(cmd, shell=True, check=True)


def update_yaml_files(aws_account_id, region):
    """Update YAML files with AWS account and region."""
    yaml_files = [
        K8S_DIR / "chrome-node" / "deployment.yaml",
        K8S_DIR / "test-controller" / "deployment.yaml"
    ]
    
    for yaml_file in yaml_files:
        content = yaml_file.read_text()
        content = content.replace('ACCOUNT_ID', aws_account_id)
        content = content.replace('REGION', region)
        yaml_file.write_text(content)


def set_chrome_node_count(count):
    """Set number of Chrome nodes."""
    yaml_file = K8S_DIR / "chrome-node" / "deployment.yaml"
    content = yaml_file.read_text()
    content = re.sub(r'replicas:\s*\d+', f'replicas: {count}', content)
    yaml_file.write_text(content)


def wait_for_chrome_nodes(node_count, timeout=300):
    """Wait for Chrome nodes to be ready."""
    print(f"Waiting for {node_count} Chrome nodes...")
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            output = run_cmd(
                "kubectl get pods -l app=chrome-node -o jsonpath='{.items[*].status.conditions[?(@.type==\"Ready\")].status}'",
                capture=True
            )
            ready = output.split()
            ready_count = sum(1 for s in ready if s == "True")
            
            if ready_count == node_count:
                print(f"All {node_count} Chrome nodes ready")
                return True
            
            print(f"Chrome nodes ready: {ready_count}/{node_count}")
        except:
            pass
        
        time.sleep(5)
    
    print("Timeout waiting for Chrome nodes")
    return False


def deploy(node_count, aws_account_id, region):
    """Deploy to Kubernetes."""
    print(f"Deploying {node_count} Chrome nodes to AWS {region}")
    
    # Update YAML files
    update_yaml_files(aws_account_id, region)
    set_chrome_node_count(node_count)
    
    # Deploy Chrome nodes
    print("\nDeploying Chrome nodes...")
    run_cmd(f"kubectl apply -f {K8S_DIR}/chrome-node/service.yaml")
    run_cmd(f"kubectl apply -f {K8S_DIR}/chrome-node/deployment.yaml")
    
    # Wait for Chrome nodes
    if not wait_for_chrome_nodes(node_count):
        print("Deployment failed")
        return
    
    # Deploy Test Controller
    print("\nDeploying Test Controller...")
    run_cmd(f"kubectl apply -f {K8S_DIR}/test-controller/deployment.yaml")
    
    # Wait and show logs
    time.sleep(10)
    print("\nTest logs:")
    try:
        pod = run_cmd(
            "kubectl get pods -l app=test-controller -o jsonpath='{.items[0].metadata.name}'",
            capture=True
        )
        if pod:
            run_cmd(f"kubectl logs -f {pod}")
    except:
        print("Could not get logs")
    
    print("\nDeployment completed")


def cleanup():
    """Delete all resources."""
    print("Cleaning up resources...")
    run_cmd(f"kubectl delete -f {K8S_DIR}/test-controller/deployment.yaml || true")
    run_cmd(f"kubectl delete -f {K8S_DIR}/chrome-node/deployment.yaml || true")
    run_cmd(f"kubectl delete -f {K8S_DIR}/chrome-node/service.yaml || true")
    print("Cleanup completed")


def main():
    parser = argparse.ArgumentParser(description="Deploy tests to Kubernetes")
    parser.add_argument('--node-count', type=int, default=1, choices=range(1, 6))
    parser.add_argument('--aws-account-id', type=str)
    parser.add_argument('--region', type=str, default='us-east-1')
    parser.add_argument('--cleanup', action='store_true')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup()
        return
    
    aws_account_id = args.aws_account_id or os.getenv("AWS_ACCOUNT_ID")
    if not aws_account_id:
        print("Error: AWS_ACCOUNT_ID required")
        return
    
    if not 1 <= args.node_count <= 5:
        print("Error: node-count must be between 1 and 5")
        return
    
    deploy(args.node_count, aws_account_id, args.region)


if __name__ == "__main__":
    main()
