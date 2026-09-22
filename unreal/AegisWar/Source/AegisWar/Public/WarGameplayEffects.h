#pragma once

#include "CoreMinimal.h"
#include "GameplayEffect.h"
#include "WarGameplayEffects.generated.h"

UCLASS()
class AEGISWAR_API UWarEnemyDamageEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UWarEnemyDamageEffect();
};

UCLASS()
class AEGISWAR_API UWarInitialAttributesEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UWarInitialAttributesEffect();
};

UCLASS()
class AEGISWAR_API UWarStrikeCostEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UWarStrikeCostEffect();
};

UCLASS()
class AEGISWAR_API UWarStrikeCooldownEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UWarStrikeCooldownEffect();
};

UCLASS()
class AEGISWAR_API UWarStrikeDamageEffect : public UGameplayEffect
{
    GENERATED_BODY()
public:
    UWarStrikeDamageEffect();
};
