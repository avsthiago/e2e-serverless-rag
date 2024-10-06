output "rag_function_url" {
  description = "Function URL for RAG function"
  value       = aws_lambda_function_url.function_url.function_url
}

output "rag_function_arn" {
  description = "Function ARN for RAG function"
  value       = module.lambda_function.lambda_function_arn
}
