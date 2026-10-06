#pragma once
#include "CoreMinimal.h"

class AActor;
struct FWarCombatUiStyle;

/** Client-only presentation of confirmed outgoing effects; never owns the recipient. */
struct FWarFloatingCombatNumber
{
    TWeakObjectPtr<AActor> Recipient;
    uint32 RecipientId = 0;
    FVector Anchor = FVector::ZeroVector;
    FName Kind;
    float Amount = 0;
    double Created = 0, Updated = 0;
    float Progress = 0, Speed = 1;
    int32 Lane = 0;
    bool bEnemy = true;
    float Lifetime = 1, Rise = 64, MaxBurst = 5;
};

namespace WarFloatingCombatText
{
    constexpr int32 MaxNumbers = 32, MaxPerRecipient = 6;
    constexpr float Lifetime = 1.f, Rise = 64.f;
    constexpr float RegionWidth = 160.f, RegionHeight = 112.f, MaxTextWidth = 56.f;
    AEGISWAR_API FVector HeadAnchor(const AActor* Recipient);
    AEGISWAR_API void Advance(TArray<FWarFloatingCombatNumber>& Numbers, double Now);
    /** RecipientId is an opaque server identity, including when the actor is not mapped yet. Zero means incoming feedback. */
    AEGISWAR_API bool Add(TArray<FWarFloatingCombatNumber>& Numbers, uint32 RecipientId, AActor* Recipient,
        FVector Anchor, FName Kind, float Amount, double Now, bool bEnemy = true, const FWarCombatUiStyle* Style = nullptr);
    AEGISWAR_API FVector2D Offset(const FWarFloatingCombatNumber& Number);
    AEGISWAR_API float Opacity(const FWarFloatingCombatNumber& Number);
}
