#include "WarProgressionRules.h"

bool WarProgression::SetGmLevel(const FWarCharacterProgression& Current, const int32 Level,
    FWarCharacterProgression& Next, FString& Error)
{
    Error.Reset();
    if (Level < 1 || Level > MaxGmLevel)
    { Error = FString::Printf(TEXT("Choose a level from 1 to %d."), MaxGmLevel); return false; }
    FWarCharacterProgression Result;
    if (!Award(Current, 0, 0, Result, Error)) return false;
    const int64 Delta = int64(Level) - Current.Level;
    const int64 Health = int64(Current.MaxHealth) + Delta * 20;
    const int64 Mana = int64(Current.MaxMana) + Delta * 10;
    const int64 Strength = int64(Current.BaseStrength) + Delta * 2;
    if (Health < 1 || Health > MAX_int32 || Mana < 1 || Mana > MAX_int32 || Strength < 0 || Strength > MAX_int32)
    { Error = TEXT("Level change would produce invalid character stats."); return false; }
    Result.Level = Level;
    Result.Xp = 0;
    Result.MaxHealth = int32(Health);
    Result.MaxMana = int32(Mana);
    Result.BaseStrength = int32(Strength);
    Next = Result;
    return true;
}

int64 WarProgression::XpForLevel(const int32 Level) { return 100 + int64(Level) * 150; }

bool WarProgression::Award(const FWarCharacterProgression& Current, const int32 Xp, const int32 Gold,
    FWarCharacterProgression& Next, FString& Error)
{
    Error.Reset();
    if (Xp < 0 || Gold < 0 || Current.Level < 1 || Current.Xp < 0 || Current.Xp >= XpForLevel(Current.Level)
        || Current.Gold < 0 || Current.Gold > MAX_int64 - Gold || Current.MaxHealth <= 0
        || Current.MaxMana <= 0 || Current.BaseStrength < 0)
    { Error = TEXT("Character reward or progression state is invalid."); return false; }
    auto Result = Current;
    Result.Xp += Xp; Result.Gold += Gold;
    // Normalized input and bounded reward sizes keep this loop below 6,000 iterations.
    while (Result.Xp >= XpForLevel(Result.Level))
    {
        if (Result.Level == MAX_int32 || Result.MaxHealth > MAX_int32 - 20
            || Result.MaxMana > MAX_int32 - 10 || Result.BaseStrength > MAX_int32 - 2)
        { Error = TEXT("Character stats exceed the supported range."); return false; }
        Result.Xp -= XpForLevel(Result.Level);
        ++Result.Level; Result.MaxHealth += 20; Result.MaxMana += 10; Result.BaseStrength += 2;
    }
    Next = Result; return true;
}
