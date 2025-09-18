"""
Intelligent Code Modifier: LLM-powered code analysis and modification system.
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
import google.generativeai as genai
import os


@dataclass
class CodeAnalysis:
    """Results of code analysis."""
    language: str
    framework: Optional[str]
    key_components: List[str]
    functions: List[Dict[str, Any]]
    classes: List[Dict[str, Any]]
    imports: List[str]
    dependencies: List[str]
    potential_issues: List[str]
    suggestions: List[str]


@dataclass
class CodeModification:
    """Represents a code modification."""
    file_path: str
    original_code: str
    modified_code: str
    explanation: str
    change_type: str  # 'update', 'remove', 'add', 'refactor'
    confidence: float


class IntelligentCodeModifier:
    """LLM-powered code analysis and modification system."""

    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    async def analyze_code(self, code: str, file_path: str) -> CodeAnalysis:
        """Analyze code structure and provide insights."""

        prompt = f"""Analyze this code file and provide structured insights:

File: {file_path}
Code:
```
{code}
```

Provide analysis in this JSON format:
{{
    "language": "detected programming language",
    "framework": "detected framework if any",
    "key_components": ["list of main components/modules"],
    "functions": [
        {{"name": "function_name", "line_start": 1, "line_end": 10, "purpose": "what it does"}}
    ],
    "classes": [
        {{"name": "class_name", "line_start": 1, "line_end": 20, "methods": ["method1", "method2"]}}
    ],
    "imports": ["list of imports/dependencies"],
    "dependencies": ["external packages used"],
    "potential_issues": ["any code smells or issues found"],
    "suggestions": ["improvement suggestions"]
}}

Focus on providing actionable insights for code modification."""

        try:
            response = await self.model.generate_content_async(prompt)

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
                return CodeAnalysis(**analysis_data)
            else:
                # Fallback basic analysis
                return self._basic_code_analysis(code, file_path)

        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._basic_code_analysis(code, file_path)

    def _basic_code_analysis(self, code: str, file_path: str) -> CodeAnalysis:
        """Fallback basic code analysis without LLM."""

        # Detect language from file extension
        ext = file_path.split('.')[-1].lower()
        language_map = {
            'py': 'python', 'js': 'javascript', 'ts': 'typescript',
            'java': 'java', 'go': 'go', 'rs': 'rust', 'cpp': 'cpp',
            'c': 'c', 'rb': 'ruby', 'php': 'php'
        }
        language = language_map.get(ext, 'unknown')

        # Basic pattern matching
        functions = []
        classes = []
        imports = []

        if language == 'python':
            # Find Python functions
            func_pattern = r'def\s+(\w+)\s*\('
            for match in re.finditer(func_pattern, code):
                functions.append({
                    "name": match.group(1),
                    "line_start": code[:match.start()].count('\n') + 1,
                    "purpose": "detected function"
                })

            # Find Python classes
            class_pattern = r'class\s+(\w+)\s*\(?[^:]*\)?\s*:'
            for match in re.finditer(class_pattern, code):
                classes.append({
                    "name": match.group(1),
                    "line_start": code[:match.start()].count('\n') + 1,
                    "methods": []
                })

            # Find imports
            import_pattern = r'^(?:from\s+\S+\s+)?import\s+(.+)$'
            for match in re.finditer(import_pattern, code, re.MULTILINE):
                imports.append(match.group(1).strip())

        return CodeAnalysis(
            language=language,
            framework=None,
            key_components=[],
            functions=functions,
            classes=classes,
            imports=imports,
            dependencies=[],
            potential_issues=[],
            suggestions=[]
        )

    async def suggest_modifications(self, code: str, file_path: str,
                                  instruction: str) -> List[CodeModification]:
        """Suggest code modifications based on instruction."""

        # First analyze the code
        analysis = await self.analyze_code(code, file_path)

        prompt = f"""You are an expert code modifier. Analyze the code and provide specific modifications based on the instruction.

File: {file_path}
Language: {analysis.language}
Current Code:
```
{code}
```

Instruction: {instruction}

Code Analysis Context:
- Functions: {[f['name'] for f in analysis.functions]}
- Classes: {[c['name'] for c in analysis.classes]}
- Imports: {analysis.imports}

Provide modifications in this JSON format:
{{
    "modifications": [
        {{
            "change_type": "update|remove|add|refactor",
            "target_section": "specific code section to modify",
            "modified_code": "the exact new code",
            "explanation": "why this change is needed",
            "confidence": 0.9,
            "line_range": {{"start": 1, "end": 10}}
        }}
    ]
}}

Rules:
1. Only suggest modifications that directly address the instruction
2. Maintain code syntax and style consistency
3. Preserve existing functionality unless explicitly asked to change it
4. Provide complete, working code sections
5. Be conservative - only modify what's necessary

Focus on being precise and actionable."""

        try:
            response = await self.model.generate_content_async(prompt)

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                modifications = []

                for mod_data in data.get('modifications', []):
                    # Apply the modification to get the full modified code
                    modified_code = self._apply_modification_to_code(
                        code, mod_data
                    )

                    modifications.append(CodeModification(
                        file_path=file_path,
                        original_code=code,
                        modified_code=modified_code,
                        explanation=mod_data.get('explanation', ''),
                        change_type=mod_data.get('change_type', 'update'),
                        confidence=mod_data.get('confidence', 0.5)
                    ))

                return modifications
            else:
                return []

        except Exception as e:
            print(f"LLM modification suggestion failed: {e}")
            return []

    def _apply_modification_to_code(self, original_code: str, modification: Dict) -> str:
        """Apply a single modification to code."""

        target_section = modification.get('target_section', '')
        new_code = modification.get('modified_code', '')
        change_type = modification.get('change_type', 'update')

        if change_type == 'remove':
            # Remove the target section
            return original_code.replace(target_section, '')

        elif change_type == 'update' or change_type == 'refactor':
            # Replace target section with new code
            if target_section in original_code:
                return original_code.replace(target_section, new_code)
            else:
                # If exact match not found, try line-based replacement
                line_range = modification.get('line_range', {})
                if line_range.get('start') and line_range.get('end'):
                    lines = original_code.split('\n')
                    start_idx = line_range['start'] - 1
                    end_idx = line_range['end']

                    # Replace the line range
                    new_lines = lines[:start_idx] + new_code.split('\n') + lines[end_idx:]
                    return '\n'.join(new_lines)
                else:
                    return original_code  # No change if can't locate target

        elif change_type == 'add':
            # Add new code (append by default)
            return original_code + '\n\n' + new_code

        return original_code

    async def validate_code_syntax(self, code: str, language: str) -> Tuple[bool, Optional[str]]:
        """Validate if the modified code has correct syntax."""

        if language == 'python':
            try:
                import ast
                ast.parse(code)
                return True, None
            except SyntaxError as e:
                return False, f"Python syntax error: {e}"

        elif language in ['javascript', 'typescript']:
            # For JS/TS, we could use a more sophisticated checker
            # For now, basic validation
            if code.count('{') != code.count('}'):
                return False, "Mismatched braces"
            if code.count('(') != code.count(')'):
                return False, "Mismatched parentheses"

        # For other languages, assume valid for now
        return True, None

    async def explain_code_changes(self, original: str, modified: str,
                                 file_path: str) -> str:
        """Generate explanation of what changed between code versions."""

        prompt = f"""Compare these two code versions and explain what changed:

File: {file_path}

Original Code:
```
{original}
```

Modified Code:
```
{modified}
```

Provide a clear, concise explanation of:
1. What was changed (functions, variables, logic, etc.)
2. Why the change might have been made
3. Any potential impacts

Keep the explanation technical but accessible."""

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Unable to generate explanation: {e}"

    async def refactor_code(self, code: str, file_path: str,
                          refactor_type: str) -> Optional[CodeModification]:
        """Perform specific refactoring operations."""

        refactor_prompts = {
            "improve_readability": "Improve code readability by adding comments, better variable names, and cleaner structure",
            "optimize_performance": "Optimize code for better performance while maintaining functionality",
            "modernize_syntax": "Update code to use modern language features and best practices",
            "extract_functions": "Extract repeated code into reusable functions",
            "simplify_logic": "Simplify complex logic and reduce code complexity",
            "add_error_handling": "Add proper error handling and validation"
        }

        instruction = refactor_prompts.get(refactor_type, refactor_type)
        modifications = await self.suggest_modifications(code, file_path, instruction)

        return modifications[0] if modifications else None


class CodeModificationTool(BaseTool):
    """Agent tool for intelligent code modification."""

    def __init__(self):
        super().__init__(
            name="intelligent_code_modifier",
            description=(
                "Analyze and modify code intelligently using LLM. Can update, remove, or refactor code "
                "based on natural language instructions. Provides syntax validation and change explanations."
            ),
        )

        # Store input schema as instance variable for reference
        self.input_schema = {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The source code to analyze/modify"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path/name for context"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["analyze", "modify", "refactor", "validate"],
                        "description": "Operation to perform"
                    },
                    "instruction": {
                        "type": "string",
                        "description": "Natural language instruction for modifications"
                    },
                    "refactor_type": {
                        "type": "string",
                        "enum": ["improve_readability", "optimize_performance", "modernize_syntax",
                                "extract_functions", "simplify_logic", "add_error_handling"],
                        "description": "Type of refactoring to perform"
                    }
                },
                "required": ["code", "file_path", "operation"]
            }
        self.modifier = IntelligentCodeModifier()

    async def run_async(self, *, args: Dict[str, Any], tool_context) -> Dict[str, Any]:
        """Execute intelligent code modification."""

        try:
            code = args["code"]
            file_path = args["file_path"]
            operation = args["operation"]

            if operation == "analyze":
                analysis = await self.modifier.analyze_code(code, file_path)
                return {
                    "status": "success",
                    "analysis": {
                        "language": analysis.language,
                        "framework": analysis.framework,
                        "functions_count": len(analysis.functions),
                        "classes_count": len(analysis.classes),
                        "imports": analysis.imports,
                        "suggestions": analysis.suggestions,
                        "potential_issues": analysis.potential_issues
                    }
                }

            elif operation == "modify":
                instruction = args.get("instruction", "")
                if not instruction:
                    return {"status": "error", "error": "No instruction provided"}

                modifications = await self.modifier.suggest_modifications(code, file_path, instruction)

                if modifications:
                    mod = modifications[0]  # Take the first suggestion

                    # Validate syntax
                    analysis = await self.modifier.analyze_code(code, file_path)
                    is_valid, error = await self.modifier.validate_code_syntax(
                        mod.modified_code, analysis.language
                    )

                    return {
                        "status": "success",
                        "original_code": mod.original_code,
                        "modified_code": mod.modified_code,
                        "explanation": mod.explanation,
                        "change_type": mod.change_type,
                        "confidence": mod.confidence,
                        "syntax_valid": is_valid,
                        "syntax_error": error
                    }
                else:
                    return {
                        "status": "no_changes",
                        "message": "No modifications suggested for the given instruction"
                    }

            elif operation == "refactor":
                refactor_type = args.get("refactor_type", "improve_readability")
                modification = await self.modifier.refactor_code(code, file_path, refactor_type)

                if modification:
                    return {
                        "status": "success",
                        "original_code": modification.original_code,
                        "modified_code": modification.modified_code,
                        "explanation": modification.explanation,
                        "refactor_type": refactor_type,
                        "confidence": modification.confidence
                    }
                else:
                    return {
                        "status": "no_changes",
                        "message": f"No refactoring suggestions for type: {refactor_type}"
                    }

            elif operation == "validate":
                analysis = await self.modifier.analyze_code(code, file_path)
                is_valid, error = await self.modifier.validate_code_syntax(code, analysis.language)

                return {
                    "status": "success",
                    "syntax_valid": is_valid,
                    "syntax_error": error,
                    "language": analysis.language
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Tool instance
intelligent_code_tool = CodeModificationTool()