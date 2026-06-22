def number_to_words_indian(number):
    """Convert a number to Indian currency words format."""
    if number == 0:
        return "Zero"

    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_below_thousand(num):
        res = ""
        if num >= 100:
            res += units[num // 100] + " Hundred "
            num %= 100
        if num >= 10 and num <= 19:
            res += teens[num - 10] + " "
        elif num >= 20 or num == 0:
            res += tens[num // 10] + " "
            if num % 10 > 0:
                res += units[num % 10] + " "
        elif num > 0:
            res += units[num] + " "
        return res.strip()

    integer_part = int(number)
    decimal_part = int(round((number - integer_part) * 100))

    words = ""
    
    # Crore
    if integer_part >= 10000000:
        words += convert_below_thousand(integer_part // 10000000) + " Crore "
        integer_part %= 10000000
    
    # Lakh
    if integer_part >= 100000:
        words += convert_below_thousand(integer_part // 100000) + " Lakh "
        integer_part %= 100000
    
    # Thousand
    if integer_part >= 1000:
        words += convert_below_thousand(integer_part // 1000) + " Thousand "
        integer_part %= 1000
    
    # Remainder
    words += convert_below_thousand(integer_part)
    
    words = words.strip() + " Rupees"
    
    if decimal_part > 0:
        words += " and " + convert_below_thousand(decimal_part) + " Paise"
    
    return words + " Only"
