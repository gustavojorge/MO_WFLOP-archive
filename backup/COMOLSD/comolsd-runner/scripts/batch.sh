#!/bin/bash

script="./main.sh"
create_folders="./smaller_scripts/create_folders.sh"

echo "Running script 1 = create_folders.sh"
bash "$create_folders"

nohup "$script" A B C &> "./logs/batch_A_B_C.txt" &
nohup "$script" D E &> "./logs/batch_D_E.txt" &

nohup "$script" F G &> "./logs/batch_F_G.txt" &
nohup "$script" H I &> "./logs/batch_H_I.txt" &

nohup "$script" J 0 &> "./logs/batch_J_0" &

start=1
end=500
step=2

for ((i=$start; i<=$end; i+=$step)); do
  batch_start=$i
  batch_end=$((i + step - 1))
  
  if ((batch_end > end)); then
    batch_end=$end
  fi

  batch=$(seq $batch_start $batch_end | tr '\n' ' ')

  nohup "$script" $batch &> "./logs/batch_${batch_start}_to_${batch_end}.txt" &
done

nohup "$script" 501 502 503 504 505 &> "./logs/batch_501_to_505.txt" &
