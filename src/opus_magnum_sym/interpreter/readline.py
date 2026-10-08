from prompt_toolkit import prompt

if __name__ == "__main__":
    answer = prompt("> ", multiline=True)
    print(f"You said: {answer}")
