#include "WarEnemyStateSubsystem.h"

FWarEnemyLife& UWarEnemyStateSubsystem::FindOrCreate(FName Zone, FName Id, float MaxHealth)
{
    const FString Key = Zone.ToString() + TEXT("/") + Id.ToString();
    if (auto* Existing = Lives.Find(Key)) return *Existing;
    FWarEnemyLife Life; Life.Health = MaxHealth;
    return Lives.Add(Key, Life);
}
