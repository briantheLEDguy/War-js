#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "WarEnemyStateSubsystem.generated.h"

struct FWarEnemyLife
{
    FGuid Event = FGuid::NewGuid();
    double RespawnAt = 0;
    float Health = 0;
};

/** Server-session state outlives streamed actors; leaving a zone cannot reset a death cooldown. */
UCLASS()
class AEGISWAR_API UWarEnemyStateSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    FWarEnemyLife& FindOrCreate(FName Zone, FName Id, float MaxHealth);
private:
    TMap<FString, FWarEnemyLife> Lives;
};
