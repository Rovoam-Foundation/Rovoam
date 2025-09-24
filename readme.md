# Rovoam

**Languages**: English | [Russian](readme.ru.md)

Rovoam is a simple Python AI agent.

## How to use

- Run src/main.py
- Type any message then hit Shift+Tab to send.
- /help for commands help

## How to use rovoam.py in your project

Import the required classes from rovoam

- Agent: ReAct agent
- Chat: simple chat
- Classifier: takes a string and returns a category, or None if it cannot answer

## Creating tools

Any function with docstring can be a tool.

Example:

```python
def test_tool(number):
  """
  test_tool.
  Multiplies number by 2
  Options:
  Number: input number
  """

  return number*2
```