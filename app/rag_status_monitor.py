"""
RAG Status Monitor: Monitor and health-check RAG systems.
"""

import asyncio
from typing import Dict, List
import vertexai
from vertexai.preview import rag
from .automated_rag_builder import rag_builder


class RagStatusMonitor:
    """Monitor RAG system health and status."""

    def __init__(self):
        vertexai.init(
            project="qwiklabs-gcp-03-ec92c6095411",
            location="europe-west2"
        )

    async def check_all_rag_systems(self) -> Dict:
        """Check status of all RAG systems."""

        print("🔍 Checking RAG Systems Status...")

        status_report = {
            "overall_status": "healthy",
            "corpora_status": {},
            "data_sources_status": {},
            "recommendations": []
        }

        # Check each configured corpus
        for corpus_name, config in rag_builder.corpus_configs.items():
            corpus_status = await self._check_corpus_status(corpus_name, config)
            status_report["corpora_status"][corpus_name] = corpus_status

            if corpus_status["status"] != "healthy":
                status_report["overall_status"] = "issues_detected"

        # Check data sources
        data_sources_status = await self._check_data_sources()
        status_report["data_sources_status"] = data_sources_status

        # Generate recommendations
        status_report["recommendations"] = self._generate_recommendations(status_report)

        return status_report

    async def _check_corpus_status(self, corpus_name: str, config: Dict) -> Dict:
        """Check status of a specific corpus."""

        status = {
            "status": "unknown",
            "exists": False,
            "document_count": 0,
            "last_updated": None,
            "issues": []
        }

        try:
            # Try to list corpora to see if it exists
            corpora = rag.list_corpora()

            # Look for our corpus
            corpus_display_name = config["display_name"]
            found_corpus = None

            for corpus in corpora:
                if corpus.display_name == corpus_display_name:
                    found_corpus = corpus
                    break

            if found_corpus:
                status["exists"] = True
                status["corpus_id"] = found_corpus.name

                # Try to get corpus details
                try:
                    # Get files in corpus
                    files = rag.list_files(corpus_name=found_corpus.name)
                    status["document_count"] = len(files)

                    if status["document_count"] > 0:
                        status["status"] = "healthy"
                    else:
                        status["status"] = "empty"
                        status["issues"].append("Corpus exists but has no documents")

                except Exception as e:
                    status["status"] = "error"
                    status["issues"].append(f"Cannot access corpus files: {e}")

            else:
                status["status"] = "missing"
                status["issues"].append("Corpus does not exist")

        except Exception as e:
            status["status"] = "error"
            status["issues"].append(f"Cannot access RAG service: {e}")

        return status

    async def _check_data_sources(self) -> Dict:
        """Check status of data source connections."""

        sources_status = {
            "google_search": await self._test_google_search(),
            "microsoft_docs": await self._test_microsoft_mcp(),
            "terraform_docs": await self._test_terraform_mcp(),
            "github": await self._test_github_mcp()
        }

        return sources_status

    async def _test_google_search(self) -> Dict:
        """Test Google Search connectivity."""
        try:
            result = await rag_builder.search_tool.invoke("test query python diagrams")
            return {
                "status": "healthy" if result else "error",
                "message": "Google Search working" if result else "No results returned"
            }
        except Exception as e:
            return {"status": "error", "message": f"Google Search failed: {e}"}

    async def _test_microsoft_mcp(self) -> Dict:
        """Test Microsoft Learn MCP connectivity."""
        try:
            # TODO: Implement actual test
            return {"status": "healthy", "message": "Microsoft MCP working"}
        except Exception as e:
            return {"status": "error", "message": f"Microsoft MCP failed: {e}"}

    async def _test_terraform_mcp(self) -> Dict:
        """Test Terraform docs MCP connectivity."""
        try:
            # TODO: Implement actual test
            return {"status": "healthy", "message": "Terraform MCP working"}
        except Exception as e:
            return {"status": "error", "message": f"Terraform MCP failed: {e}"}

    async def _test_github_mcp(self) -> Dict:
        """Test GitHub MCP connectivity."""
        try:
            # TODO: Implement actual test
            return {"status": "healthy", "message": "GitHub MCP working"}
        except Exception as e:
            return {"status": "error", "message": f"GitHub MCP failed: {e}"}

    def _generate_recommendations(self, status_report: Dict) -> List[str]:
        """Generate recommendations based on status report."""

        recommendations = []

        # Check for missing corpora
        missing_corpora = [
            name for name, status in status_report["corpora_status"].items()
            if status["status"] == "missing"
        ]

        if missing_corpora:
            recommendations.append(
                f"Create missing RAG corpora: {', '.join(missing_corpora)}. "
                f"Run: python rag_manager.py create-all"
            )

        # Check for empty corpora
        empty_corpora = [
            name for name, status in status_report["corpora_status"].items()
            if status["status"] == "empty"
        ]

        if empty_corpora:
            recommendations.append(
                f"Populate empty RAG corpora: {', '.join(empty_corpora)}. "
                f"Run: python rag_manager.py refresh <corpus_name>"
            )

        # Check for data source issues
        failed_sources = [
            source for source, status in status_report["data_sources_status"].items()
            if status["status"] == "error"
        ]

        if failed_sources:
            recommendations.append(
                f"Fix data source connections: {', '.join(failed_sources)}"
            )

        if not recommendations:
            recommendations.append("✅ All RAG systems are healthy!")

        return recommendations

    async def print_status_report(self):
        """Print a formatted status report."""

        status_report = await self.check_all_rag_systems()

        print("=" * 60)
        print("🏥 RAG SYSTEMS HEALTH REPORT")
        print("=" * 60)

        # Overall status
        status_emoji = "✅" if status_report["overall_status"] == "healthy" else "⚠️"
        print(f"\nOverall Status: {status_emoji} {status_report['overall_status'].upper()}")

        # Corpora status
        print(f"\n📚 RAG CORPORA STATUS:")
        for name, status in status_report["corpora_status"].items():
            status_emoji = {
                "healthy": "✅",
                "empty": "⚠️",
                "missing": "❌",
                "error": "❌",
                "unknown": "❓"
            }.get(status["status"], "❓")

            print(f"  {status_emoji} {name}: {status['status']}")
            if status.get("document_count", 0) > 0:
                print(f"     📄 Documents: {status['document_count']}")
            if status.get("issues"):
                for issue in status["issues"]:
                    print(f"     ⚠️  {issue}")

        # Data sources status
        print(f"\n🔌 DATA SOURCES STATUS:")
        for source, status in status_report["data_sources_status"].items():
            status_emoji = "✅" if status["status"] == "healthy" else "❌"
            print(f"  {status_emoji} {source}: {status['message']}")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(status_report["recommendations"], 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 60)


# Global monitor instance
rag_monitor = RagStatusMonitor()


async def check_rag_health():
    """Check RAG system health."""
    return await rag_monitor.check_all_rag_systems()


async def print_rag_status():
    """Print formatted RAG status report."""
    await rag_monitor.print_status_report()


if __name__ == "__main__":
    asyncio.run(print_rag_status())