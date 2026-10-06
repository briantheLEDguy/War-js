#pragma once
#include "CoreMinimal.h"
#include "WarSiegeRules.generated.h"

UENUM()
enum class EWarSiegePhase : uint8 { Waiting, Active, Transition, Finished };
UENUM()
enum class EWarSiegeRole : uint8 { Tank, Healer, Damage };
UENUM()
enum class EWarSiegeScenario : uint8 { FullSiege, LowerCity };
UENUM()
enum class EWarSiegeDecision : uint8 { Evade, Recover, Combat, Objective, Follow };
UENUM()
enum class EWarSiegeUnit : uint8 { Participant, Crew, Guard, Commander, Emplacement };

USTRUCT()
struct FWarSiegeState
{
    GENERATED_BODY()
    // A round records its rules; v1 snapshots retain their sequential courtyard.
    UPROPERTY() int32 RulesVersion = 2;
    UPROPERTY() EWarSiegePhase Phase = EWarSiegePhase::Waiting;
    UPROPERTY() EWarSiegeScenario Scenario = EWarSiegeScenario::FullSiege;
    UPROPERTY() int32 Capacity = 6;
    UPROPERTY() int32 Stage = 0;
    UPROPERTY() int32 Objective = 0;
    UPROPERTY() float Progress = 0;
    UPROPERTY() float LeftProgress = 0;
    UPROPERTY() float RightProgress = 0;
    UPROPERTY() double LeftAbsence = 0;
    UPROPERTY() double RightAbsence = 0;
    UPROPERTY() uint8 MainClaims = 0;
    UPROPERTY() float OptionalProgress = 0;
    UPROPERTY() bool bOptionalComplete = false;
    UPROPERTY() uint8 OptionalClaims = 0;
    UPROPERTY() bool bOvertime = false;
    UPROPERTY() bool bAttackersWon = false;
    UPROPERTY() double Remaining = 840;
    UPROPERTY() double Absence = 0;
    UPROPERTY() double OptionalAbsence = 0;
    UPROPERTY() double OvertimeAbsence = 0;
    UPROPERTY() int32 ResultCount = 0;
    UPROPERTY() double Elapsed = 0;
    UPROPERTY() double ContestedSeconds = 0;
    UPROPERTY() TArray<double> MilestoneSeconds;
};

/** Inputs are sampled from server actors, never submitted by a client. */
struct FWarSiegePresence
{
    int32 Attackers = 0, Defenders = 0, OptionalAttackers = 0, OptionalDefenders = 0;
    int32 LeftAttackers = 0, LeftDefenders = 0, RightAttackers = 0, RightDefenders = 0;
    bool bCrewAlive = true, bCommanderDead = false, bRecentCommanderDamage = false, bEscortAtCheckpoint = true;
};

namespace WarSiege
{
    constexpr double StageSeconds = 840, TransitionSeconds = 60, OvertimeSeconds = 120;
    constexpr double WaveSeconds = 20, CrewReplacementSeconds = 30, CommanderResetSeconds = 15;
    AEGISWAR_API bool ValidCapacity(int32 Capacity);
    AEGISWAR_API float HealthScale(int32 Capacity);
    AEGISWAR_API int32 Reinforcements(int32 Capacity, bool bSabotaged);
    AEGISWAR_API float ParticipationRate(int32 Count, bool bEscort = false);
    AEGISWAR_API int32 FinalObjective(int32 Stage);
    AEGISWAR_API bool IsEscort(const FWarSiegeState& State);
    AEGISWAR_API uint16 ClaimedObjectives(const FWarSiegeState& State);
    AEGISWAR_API bool CenterUnlocked(const FWarSiegeState& State);
    AEGISWAR_API bool RequiresCrew(const FWarSiegeState& State);
    AEGISWAR_API bool Start(FWarSiegeState& State, int32 Capacity, EWarSiegeScenario Scenario = EWarSiegeScenario::FullSiege, int32 RulesVersion = 2);
    AEGISWAR_API void Tick(FWarSiegeState& State, const FWarSiegePresence& Presence, double Delta);
    AEGISWAR_API EWarSiegeRole MissingRole(int32 Capacity, int32 Tanks, int32 Healers);
    AEGISWAR_API EWarSiegeDecision Decide(bool bHazard, bool bRecovering, float HealthFraction,
        bool bThreatInLeash, bool bObjectiveNearby, bool bLeaderAvailable);
}
