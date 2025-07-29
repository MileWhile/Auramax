#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Aura Intelligent Retrieval Engine
Tests document processing, RAG Q&A, session management, and error handling
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any
import sys
import os

# Backend URL from frontend/.env
BACKEND_URL = "https://efadae81-5009-4f5f-a72a-bb84ffa575ae.preview.emergentagent.com/api"

class AuraBackendTester:
    def __init__(self):
        self.session = None
        self.test_results = []
        
    async def setup(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
        )
        
    async def cleanup(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
    
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Dict = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
        print()
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response": response_data
        })
    
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            async with self.session.get(f"{BACKEND_URL}/health") as response:
                data = await response.json()
                
                if response.status == 200 and data.get("status") == "healthy":
                    self.log_test("Health Check", True, "System is healthy")
                    return True
                else:
                    self.log_test("Health Check", False, f"Status: {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    async def test_document_processing_pdf(self):
        """Test PDF document processing with multiple questions"""
        test_data = {
            "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "questions": [
                "What is the main topic of this document?",
                "What are the key points mentioned?",
                "Can you summarize the content in 2-3 sentences?"
            ]
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BACKEND_URL}/hackrx/run",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                processing_time = time.time() - start_time
                data = await response.json()
                
                if response.status == 200:
                    # Validate response structure
                    required_fields = ["answers", "metadata", "processing_time", "cache_hit", "request_id"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if missing_fields:
                        self.log_test("PDF Processing - Response Structure", False, 
                                    f"Missing fields: {missing_fields}", data)
                        return False
                    
                    # Validate answers
                    if len(data["answers"]) != len(test_data["questions"]):
                        self.log_test("PDF Processing - Answer Count", False,
                                    f"Expected {len(test_data['questions'])} answers, got {len(data['answers'])}", data)
                        return False
                    
                    # Check if answers are meaningful (not empty or error messages)
                    valid_answers = 0
                    for i, answer in enumerate(data["answers"]):
                        if answer and len(answer.strip()) > 10 and "error" not in answer.lower():
                            valid_answers += 1
                    
                    if valid_answers >= 2:  # At least 2 out of 3 should be valid
                        self.log_test("PDF Processing", True, 
                                    f"Processed in {processing_time:.2f}s, {valid_answers}/3 valid answers")
                        
                        # Test session storage
                        session_id = data["metadata"].get("session_id")
                        if session_id:
                            await self.test_session_history(session_id)
                        
                        return True
                    else:
                        self.log_test("PDF Processing - Answer Quality", False,
                                    f"Only {valid_answers}/3 answers were valid", data)
                        return False
                else:
                    self.log_test("PDF Processing", False, f"HTTP {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("PDF Processing", False, f"Exception: {str(e)}")
            return False
    
    async def test_document_processing_txt(self):
        """Test TXT document processing"""
        test_data = {
            "documents": "https://www.gutenberg.org/files/74/74-0.txt",  # Sample text file
            "questions": [
                "What is this text about?",
                "Who is the main character mentioned?"
            ]
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/hackrx/run",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200 and len(data.get("answers", [])) == 2:
                    # Check if at least one answer is meaningful
                    valid_answers = sum(1 for answer in data["answers"] 
                                      if answer and len(answer.strip()) > 10)
                    
                    if valid_answers >= 1:
                        self.log_test("TXT Processing", True, f"{valid_answers}/2 valid answers")
                        return True
                    else:
                        self.log_test("TXT Processing - Answer Quality", False, "No valid answers", data)
                        return False
                else:
                    self.log_test("TXT Processing", False, f"HTTP {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("TXT Processing", False, f"Exception: {str(e)}")
            return False
    
    async def test_multiple_questions_rag(self):
        """Test RAG with multiple complex questions"""
        test_data = {
            "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "questions": [
                "What is the primary purpose of this document?",
                "Are there any specific technical details mentioned?",
                "What would be the main takeaway for a reader?",
                "Does the document contain any recommendations?",
                "What type of audience is this document intended for?"
            ]
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BACKEND_URL}/hackrx/run",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                processing_time = time.time() - start_time
                data = await response.json()
                
                if response.status == 200:
                    answers = data.get("answers", [])
                    if len(answers) == 5:
                        # Check answer quality and diversity
                        valid_answers = 0
                        unique_answers = set()
                        
                        for answer in answers:
                            if answer and len(answer.strip()) > 15:
                                valid_answers += 1
                                # Check for uniqueness (not identical responses)
                                unique_answers.add(answer[:50])  # First 50 chars for uniqueness check
                        
                        if valid_answers >= 4 and len(unique_answers) >= 3:
                            self.log_test("Multiple Questions RAG", True,
                                        f"5 questions processed in {processing_time:.2f}s, {valid_answers} valid answers")
                            return True
                        else:
                            self.log_test("Multiple Questions RAG - Quality", False,
                                        f"Valid: {valid_answers}/5, Unique: {len(unique_answers)}", data)
                            return False
                    else:
                        self.log_test("Multiple Questions RAG - Count", False,
                                    f"Expected 5 answers, got {len(answers)}", data)
                        return False
                else:
                    self.log_test("Multiple Questions RAG", False, f"HTTP {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("Multiple Questions RAG", False, f"Exception: {str(e)}")
            return False
    
    async def test_session_history(self, session_id: str):
        """Test session history retrieval"""
        try:
            async with self.session.get(f"{BACKEND_URL}/sessions/{session_id}/history") as response:
                data = await response.json()
                
                if response.status == 200:
                    history = data.get("history", [])
                    if len(history) > 0:
                        # Check if history entries have required fields
                        valid_entries = 0
                        for entry in history:
                            if "question" in entry and "answer" in entry and "timestamp" in entry:
                                valid_entries += 1
                        
                        if valid_entries == len(history):
                            self.log_test("Session History", True, f"{len(history)} history entries retrieved")
                            return True
                        else:
                            self.log_test("Session History - Structure", False,
                                        f"Invalid entries: {len(history) - valid_entries}/{len(history)}", data)
                            return False
                    else:
                        self.log_test("Session History - Empty", False, "No history entries found", data)
                        return False
                else:
                    self.log_test("Session History", False, f"HTTP {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("Session History", False, f"Exception: {str(e)}")
            return False
    
    async def test_error_handling_invalid_url(self):
        """Test error handling with invalid document URL"""
        test_data = {
            "documents": "https://invalid-url-that-does-not-exist.com/fake.pdf",
            "questions": ["What is this about?"]
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/hackrx/run",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                # Should return an error (4xx or 5xx status)
                if response.status >= 400:
                    self.log_test("Error Handling - Invalid URL", True, 
                                f"Correctly returned HTTP {response.status}")
                    return True
                else:
                    self.log_test("Error Handling - Invalid URL", False,
                                f"Should have failed but returned HTTP {response.status}", data)
                    return False
                    
        except Exception as e:
            # Network errors are expected for invalid URLs
            self.log_test("Error Handling - Invalid URL", True, f"Network error as expected: {str(e)}")
            return True
    
    async def test_error_handling_empty_questions(self):
        """Test error handling with empty questions"""
        test_data = {
            "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "questions": []
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/hackrx/run",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                # Should return validation error (422)
                if response.status == 422:
                    self.log_test("Error Handling - Empty Questions", True,
                                "Correctly rejected empty questions list")
                    return True
                else:
                    self.log_test("Error Handling - Empty Questions", False,
                                f"Expected HTTP 422, got {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("Error Handling - Empty Questions", False, f"Exception: {str(e)}")
            return False
    
    async def test_gemini_integration(self):
        """Test Gemini integration with a simple document"""
        test_data = {
            "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "questions": ["Please analyze this document and tell me what you can extract from it."]
        }
        
        try:
            async with self.session.post(
                f"{BACKEND_URL}/hackrx/run",
                json=test_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    answer = data.get("answers", [""])[0]
                    metadata = data.get("metadata", {})
                    
                    # Check if Gemini model is mentioned in metadata
                    model_used = metadata.get("model_used", "")
                    if "gemini" in model_used.lower():
                        # Check if answer shows signs of AI analysis
                        if answer and len(answer) > 20:
                            self.log_test("Gemini Integration", True,
                                        f"Model: {model_used}, Answer length: {len(answer)} chars")
                            return True
                        else:
                            self.log_test("Gemini Integration - Answer Quality", False,
                                        f"Answer too short: {len(answer)} chars", data)
                            return False
                    else:
                        self.log_test("Gemini Integration - Model", False,
                                    f"Expected Gemini model, got: {model_used}", data)
                        return False
                else:
                    self.log_test("Gemini Integration", False, f"HTTP {response.status}", data)
                    return False
                    
        except Exception as e:
            self.log_test("Gemini Integration", False, f"Exception: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Aura Intelligent Retrieval Engine Backend Tests")
        print("=" * 60)
        
        await self.setup()
        
        try:
            # Test health first
            health_ok = await self.test_health_endpoint()
            if not health_ok:
                print("❌ Health check failed - aborting remaining tests")
                return
            
            # Core functionality tests
            await self.test_document_processing_pdf()
            await self.test_document_processing_txt()
            await self.test_multiple_questions_rag()
            await self.test_gemini_integration()
            
            # Error handling tests
            await self.test_error_handling_invalid_url()
            await self.test_error_handling_empty_questions()
            
        finally:
            await self.cleanup()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! Backend is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Check details above.")
            
        return passed == total

async def main():
    """Main test runner"""
    tester = AuraBackendTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())