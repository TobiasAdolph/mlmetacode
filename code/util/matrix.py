def getRow(matrix, idx):
    return [matrix[idx][x] for x in range(0, len(matrix))]

def getCol(matrix,idx):
    return [matrix[x][idx] for x in range(0, len(matrix))]

def total(matrix):
    total = 0
    for i in range(0, len(matrix)):
        total += sum(getRow(matrix, i))
    return total

def fpr(cfm, idx):
    return (sum(getCol(cfm, idx)) - cfm[idx,idx])/ (
            total(cfm) - sum(getRow(cfm, idx)))

def spec(cfm, idx):
    return 1 - fpr(cfm, idx)

def sens(cfm, idx):
    return (cfm[idx,idx]/sum(getRow(cfm,idx)))
