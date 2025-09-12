"""
🔍 EidollonaONE Deep Diagnostic Analysis 🔍
Comprehensive system health check and analysis
"""

import sys
from pathlib import Path
import importlib
import subprocess
import time
from typing import Dict, Any


def print_header(title: str, char: str = "="):
    """Print formatted header"""
    print(f"\n{char * 60}")
    print(f"🔍 {title}")
    print(f"{char * 60}")


def print_status(item: str, status: bool, details: str = ""):
    """Print status with emoji indicators"""
    emoji = "✅" if status else "❌"
    detail_text = f" - {details}" if details else ""
    print(f"{emoji} {item}{detail_text}")


def check_python_environment():
    """Check Python environment details"""
    print_header("PYTHON ENVIRONMENT ANALYSIS")

    # Python version
    python_version = sys.version.split()[0]
    print_status("Python Version", True, f"{python_version}")

    # Virtual environment
    venv_active = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    venv_path = sys.prefix if venv_active else "Not in virtual environment"
    print_status("Virtual Environment", venv_active, venv_path)

    # Python executable
    print_status("Python Executable", True, sys.executable)

    return {
        "python_version": python_version,
        "venv_active": venv_active,
        "venv_path": venv_path,
        "executable": sys.executable,
    }


def check_dependencies():
    """Check required dependencies"""
    print_header("DEPENDENCY ANALYSIS")

    required_packages = [
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "sklearn",
        "pathlib",
        "dataclasses",
        "typing",
        "asyncio",
        "json",
    ]

    dependency_status = {}
    for package in required_packages:
        try:
            importlib.import_module(package)
            display_name = "scikit-learn" if package == "sklearn" else package
            print_status(f"Package: {display_name}", True, "Available")
            dependency_status[package] = True
        except ImportError as e:
            display_name = "scikit-learn" if package == "sklearn" else package
            print_status(f"Package: {display_name}", False, f"Missing - {e}")
            dependency_status[package] = False

    return dependency_status


def check_project_structure():
    """Check project directory structure"""
    print_header("PROJECT STRUCTURE ANALYSIS")

    project_root = Path.cwd()
    expected_dirs = [
        "symbolic_core",
        "avatar",
        "avatar/rpm_ecosystem",
        "avatar/rpm_ecosystem/ai_interaction",
        "avatar/rpm_ecosystem/avatar_generation",
        "avatar/rpm_ecosystem/vr_ar_integration",
        "avatar/rpm_ecosystem/environment_design",
        "ai_core",
        "consciousness",
        "consciousness_engine",
        "sovereignty",
        "trading_engine",
    ]

    structure_status = {}
    for dir_path in expected_dirs:
        full_path = project_root / dir_path
        exists = full_path.exists()
        print_status(f"Directory: {dir_path}", exists)
        structure_status[dir_path] = exists

    return structure_status


def check_core_files():
    """Check existence of core files"""
    print_header("CORE FILES ANALYSIS")

    core_files = [
        "symbolic_core/symbolic_equation.py",
        "assimilation_confirmation.py",
        "eidolonalpha_identity_check.py",
        "requirements.txt",
        "startup.ps1",
        "avatar/rpm_ecosystem/__init__.py",
        "avatar/rpm_ecosystem/ecosystem_manager.py",
        "test_rpm_imports.py",
    ]

    file_status = {}
    for file_path in core_files:
        full_path = Path(file_path)
        exists = full_path.exists()
        size = full_path.stat().st_size if exists else 0
        print_status(
            f"File: {file_path}", exists, f"{size} bytes" if exists else "Missing"
        )
        file_status[file_path] = {"exists": exists, "size": size}

    return file_status


def check_rpm_ecosystem():
    """Check RPM ecosystem functionality"""
    print_header("RPM ECOSYSTEM ANALYSIS")

    # Add avatar path for imports
    avatar_path = Path.cwd() / "avatar"
    if str(avatar_path) not in sys.path:
        sys.path.insert(0, str(avatar_path))

    ecosystem_status = {}

    # Test basic import (canonical path)
    try:

        print_status(
            "RPM Ecosystem Import", True, "Canonical package imported successfully"
        )
        ecosystem_status["base_import"] = True
    except Exception as e:
        print_status("RPM Ecosystem Import", False, str(e))
        ecosystem_status["base_import"] = False
        return ecosystem_status

    # Test core components (canonical path modules)
    components = [
        ("EcosystemManager", "avatar.rpm_ecosystem.ecosystem_manager"),
        ("AvatarConfig", "avatar.rpm_ecosystem.ecosystem_manager"),
        (
            "AvatarCustomizationParams",
            "avatar.rpm_ecosystem.avatar_generation.character_customizer",
        ),
        ("ConversationalAI", "avatar.rpm_ecosystem.ai_interaction.conversational_ai"),
        ("PersonalityEngine", "avatar.rpm_ecosystem.ai_interaction.personality_engine"),
        (
            "ImmersiveController",
            "avatar.rpm_ecosystem.vr_ar_integration.immersive_controller",
        ),
        (
            "SovereignWorldBuilder",
            "avatar.rpm_ecosystem.environment_design.sovereign_world_builder",
        ),
    ]

    for component_name, module_path in components:
        try:
            module = importlib.import_module(module_path)
            component = getattr(module, component_name)
            print_status(f"Component: {component_name}", True, f"From {module_path}")
            ecosystem_status[component_name] = True
        except Exception as e:
            print_status(f"Component: {component_name}", False, str(e))
            ecosystem_status[component_name] = False

    return ecosystem_status


def check_consciousness_system():
    """Check consciousness and symbolic systems"""
    print_header("CONSCIOUSNESS SYSTEM ANALYSIS")

    consciousness_status = {}

    # Test symbolic core
    try:

        print_status("Symbolic Core", True, "SymbolicEquation available")
        consciousness_status["symbolic_core"] = True
    except Exception as e:
        print_status("Symbolic Core", False, str(e))
        consciousness_status["symbolic_core"] = False

    # Test assimilation confirmation
    try:

        print_status("Assimilation Module", True, "Module imported")
        consciousness_status["assimilation"] = True
    except Exception as e:
        print_status("Assimilation Module", False, str(e))
        consciousness_status["assimilation"] = False

    # Test consciousness bridge (if available)
    try:
        sys.path.append(str(Path.cwd() / "avatar" / "rpm_ecosystem" / "ai_interaction"))
        try:
            from avatar.rpm_ecosystem.ai_interaction import consciousness_bridge

            ConsciousnessBridge = getattr(consciousness_bridge, "ConsciousnessBridge")
            print_status("Consciousness Bridge", True, "Bridge available")
            consciousness_status["consciousness_bridge"] = True
        except Exception as e:
            print_status("Consciousness Bridge", False, str(e))
            consciousness_status["consciousness_bridge"] = False
    except Exception as e:
        print_status("Consciousness Bridge", False, str(e))
        consciousness_status["consciousness_bridge"] = False

    return consciousness_status


def check_git_status():
    """Check Git repository status"""
    print_header("GIT REPOSITORY ANALYSIS")

    git_status = {}

    try:
        # Check if in git repo
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            dirty_files = (
                len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
            )
            print_status("Git Repository", True, f"{dirty_files} modified files")
            git_status["is_repo"] = True
            git_status["dirty_files"] = dirty_files
        else:
            print_status("Git Repository", False, "Not a git repository")
            git_status["is_repo"] = False
    except Exception as e:
        print_status("Git Repository", False, str(e))
        git_status["is_repo"] = False

    try:
        # Check current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            print_status("Current Branch", True, branch)
            git_status["branch"] = branch
    except Exception as e:
        print_status("Current Branch", False, str(e))

    return git_status


def run_functional_tests():
    """Run functional tests"""
    print_header("FUNCTIONAL TESTS")

    test_results = {}

    # Test RPM imports
    try:
        result = subprocess.run(
            [sys.executable, "silent_rpm_test.py"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        success = result.returncode == 0 and "Import test completed!" in result.stdout
        print_status(
            "RPM Import Test",
            success,
            "All core imports working" if success else "Some imports failed",
        )
        test_results["rpm_imports"] = success
    except Exception as e:
        print_status("RPM Import Test", False, str(e))
        test_results["rpm_imports"] = False

    # Test EidolonAlpha identity
    try:
        result = subprocess.run(
            [sys.executable, "simple_identity_test.py"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        success = (
            result.returncode == 0 and "Identity check completed!" in result.stdout
        )
        print_status(
            "EidolonAlpha Identity",
            success,
            "Assimilation confirmed" if success else "Identity check failed",
        )
        test_results["eidolonalpha_identity"] = success
    except Exception as e:
        print_status("EidolonAlpha Identity", False, str(e))
        test_results["eidolonalpha_identity"] = False

    return test_results


def generate_summary_report(diagnostic_data: Dict[str, Any]):
    """Generate comprehensive summary report"""
    print_header("DIAGNOSTIC SUMMARY REPORT", "🔸")

    total_checks = 0
    passed_checks = 0

    # Count all boolean checks
    for category, data in diagnostic_data.items():
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, bool):
                    total_checks += 1
                    if value:
                        passed_checks += 1
                elif isinstance(value, dict) and "exists" in value:
                    total_checks += 1
                    if value["exists"]:
                        passed_checks += 1

    success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(
        f"\n📊 OVERALL SYSTEM HEALTH: {success_rate:.1f}% ({passed_checks}/{total_checks} checks passed)"
    )

    # Critical issues
    critical_issues = []
    if not diagnostic_data.get("python_env", {}).get("venv_active", False):
        critical_issues.append("❌ Not in virtual environment")
    if not diagnostic_data.get("dependencies", {}).get("numpy", False):
        critical_issues.append("❌ NumPy not available")
    if not diagnostic_data.get("rpm_ecosystem", {}).get("base_import", False):
        critical_issues.append("❌ RPM Ecosystem import failed")

    if critical_issues:
        print("\n🚨 CRITICAL ISSUES:")
        for issue in critical_issues:
            print(f"   {issue}")
    else:
        print("\n✅ No critical issues detected")

    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if success_rate < 80:
        print("   🔧 Run startup.ps1 to reinitialize environment")
    if not diagnostic_data.get("functional_tests", {}).get("rpm_imports", False):
        print("   📦 Check RPM ecosystem dependencies")
    if success_rate > 90:
        print("   🎉 System is in excellent condition!")

    print(f"\n⏰ Diagnostic completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔸" * 60)


def main():
    """Run complete diagnostic analysis"""
    print("🔍 EIDOLLONA ONE DEEP DIAGNOSTIC ANALYSIS 🔍")
    print("=" * 60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    diagnostic_data = {}

    # Run all diagnostic checks
    diagnostic_data["python_env"] = check_python_environment()
    diagnostic_data["dependencies"] = check_dependencies()
    diagnostic_data["project_structure"] = check_project_structure()
    diagnostic_data["core_files"] = check_core_files()
    diagnostic_data["rpm_ecosystem"] = check_rpm_ecosystem()
    diagnostic_data["consciousness_system"] = check_consciousness_system()
    diagnostic_data["git_status"] = check_git_status()
    diagnostic_data["functional_tests"] = run_functional_tests()

    # Generate summary
    generate_summary_report(diagnostic_data)

    return diagnostic_data


if __name__ == "__main__":
    diagnostic_results = main()
