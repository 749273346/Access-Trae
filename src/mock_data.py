# Mock data for testing without API keys

MOCK_TRANSCRIPT_PYTHON = """
Hey everyone, welcome back to the channel. Today we're going to talk about how to automate Excel with Python in just 5 minutes.
First, you need to install the pandas library. You can do this by running pip install pandas.
Okay, let's look at the code.
Import pandas as pd.
data = pd.read_excel('data.xlsx')
print(data.head())
Now, let's say we want to filter the data where the 'Sales' column is greater than 100.
filtered_data = data[data['Sales'] > 100]
Finally, we save this to a new file.
filtered_data.to_excel('output.xlsx', index=False)
And that's it! You've just automated a simple Excel task.
"""

MOCK_TRANSCRIPT_GENERIC = """
This is a generic video about productivity.
The key to productivity is focus.
Technique number one: Pomodoro. Work for 25 minutes, break for 5.
Technique number two: Time blocking. Schedule your day in blocks.
That's all for today.
"""
