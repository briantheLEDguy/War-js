#pragma once
#include "CoreMinimal.h"

class FJsonObject;

/** Source statistics, in Unreal centimetres, for melee raiders and passive training targets. */
struct AEGISWAR_API FWarEnemyDefinition
{
    FName Zone, Id, Profile;
    FString Name;
    int32 Level = 0;
    float MaxHealth = 0, AggroRange = 0, AttackRange = 0, PreferredRange = 0, MoveSpeed = 0;
    int32 AttackDamage = 0;
    bool bTrainingDummy = false;
    FString StaticModel;
};

namespace WarEnemies
{
    constexpr double LeashRange = 2500;
    constexpr double RespawnSeconds = 15;
    AEGISWAR_API bool Parse(const TSharedPtr<const FJsonObject>& Catalog, FName Zone, FName Id,
        FWarEnemyDefinition& Out, FString& Error);
    AEGISWAR_API bool CanEngage(bool bAlive, bool bVisible, FName EnemyZone, FName PlayerZone,
        double DistanceSquared, double HeightDifference, double Range);
}
