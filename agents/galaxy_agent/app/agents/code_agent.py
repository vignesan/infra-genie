# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from google.adk.agents import Agent
from ..standalone_code_modifier import code_modifier


def analyze_code(code: str, file_path: str = "code.py") -> str:
    """Analyze code structure and provide insights."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        analysis = loop.run_until_complete(
            code_modifier.analyze_code(code, file_path)
        )

        loop.close()

        result = f"Code Analysis for {file_path}:\n"
        result += f"Language: {analysis.language}\n"
        result += f"Functions: {len(analysis.functions)} found\n"
        result += f"Classes: {len(analysis.classes)} found\n"

        if analysis.functions:
            result += "Functions:\n"
            for func in analysis.functions[:3]:
                result += f"  - {func['name']} (line {func.get('line_start', 'unknown')})\n"

        if analysis.potential_issues:
            result += "Potential Issues:\n"
            for issue in analysis.potential_issues:
                result += f"  - {issue}\n"

        if analysis.suggestions:
            result += "Suggestions:\n"
            for suggestion in analysis.suggestions:
                result += f"  - {suggestion}\n"

        return result

    except Exception as e:
        return f"Analysis failed: {str(e)}"


def modify_code(code: str, instruction: str, file_path: str = "code.py") -> str:
    """Modify code based on natural language instruction."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            code_modifier.workflow_analyze_and_modify(code, file_path, instruction)
        )

        loop.close()

        if result['status'] == 'success':
            modification = result['modification']
            response = f"Code Modification Results:\n"
            response += f"Change Type: {modification['change_type']}\n"
            response += f"Confidence: {modification['confidence']}\n"
            response += f"Explanation: {modification['explanation']}\n"
            response += f"Syntax Valid: {modification['syntax_valid']}\n"

            if modification['syntax_error']:
                response += f"Syntax Error: {modification['syntax_error']}\n"

            response += "\n=== MODIFIED CODE ===\n"
            response += modification['modified_code']

            return response
        else:
            return f"No modifications suggested: {result.get('message', 'Unknown reason')}"

    except Exception as e:
        return f"Modification failed: {str(e)}"


def refactor_code(code: str, refactor_type: str = "improve_readability", file_path: str = "code.py") -> str:
    """Refactor code using predefined patterns."""
    refactor_instructions = {
        "improve_readability": "Improve code readability by adding comments, better variable names, and cleaner structure",
        "optimize_performance": "Optimize code for better performance while maintaining functionality",
        "modernize_syntax": "Update code to use modern language features and best practices",
        "extract_functions": "Extract repeated code into reusable functions",
        "simplify_logic": "Simplify complex logic and reduce code complexity",
        "add_error_handling": "Add proper error handling and validation"
    }

    instruction = refactor_instructions.get(refactor_type, refactor_type)
    return modify_code(code, instruction, file_path)


def validate_code_syntax(code: str, file_path: str = "code.py") -> str:
    """Validate code syntax."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        analysis = loop.run_until_complete(
            code_modifier.analyze_code(code, file_path)
        )

        is_valid, error = loop.run_until_complete(
            code_modifier.validate_code_syntax(code, analysis.language)
        )

        loop.close()

        if is_valid:
            return f"✅ Code syntax is valid for {analysis.language}"
        else:
            return f"❌ Syntax error in {analysis.language}: {error}"

    except Exception as e:
        return f"Validation failed: {str(e)}"


code_agent = Agent(
    name="galaxy_code_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are the Galaxy Code Agent - specialized in intelligent code analysis and modification. "
        "Your expertise includes code analysis, modification, refactoring, and syntax validation using LLM-powered analysis. "
        "\n\nAvailable tools:\n"
        "- analyze_code: Analyze code structure and provide insights\n"
        "- modify_code: Modify code based on natural language instructions\n"
        "- refactor_code: Refactor code using predefined patterns\n"
        "- validate_code_syntax: Check code syntax validity\n"
        "\nFor code modification requests, always analyze first, then modify based on the instruction."
    ),
    tools=[analyze_code, modify_code, refactor_code, validate_code_syntax],
)