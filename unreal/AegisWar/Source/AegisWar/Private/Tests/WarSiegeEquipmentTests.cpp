#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarSiegeRules.h"
#include "WarSiegeEquipment.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSiegeOwnershipTest,"AegisWar.Foundation.SiegeOwnership",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarSiegeOwnershipTest::RunTest(const FString& Parameters)
{
    FWarSiegeState S; WarSiege::Start(S,6,EWarSiegeScenario::LowerCity);
    FWarSiegePresence P; P.Attackers=6;
    WarSiege::Tick(S,P,20);
    TestEqual(TEXT("Partial capture does not raise a standard"),WarSiege::ClaimedObjectives(S),uint16(0));
    P.Defenders=1; WarSiege::Tick(S,P,20);
    TestEqual(TEXT("Contesting cannot claim ownership"),WarSiege::ClaimedObjectives(S),uint16(0));
    P.Defenders=0; WarSiege::Tick(S,P,30);
    TestEqual(TEXT("Supply claim raises only its standard"),WarSiege::ClaimedObjectives(S),uint16(1));
    P.bEscortAtCheckpoint=false;WarSiege::Tick(S,P,100);
    TestEqual(TEXT("Timer cannot raise a checkpoint standard ahead of the convoy"),WarSiege::ClaimedObjectives(S),uint16(1));
    P.bEscortAtCheckpoint=true;
    for (int I=0;I<3;++I) WarSiege::Tick(S,P,100);
    TestEqual(TEXT("Lower-city win owns exactly four objectives"),WarSiege::ClaimedObjectives(S),uint16(15));
    S.bAttackersWon=false;
    TestEqual(TEXT("Defender result preserves claims"),WarSiege::ClaimedObjectives(S),uint16(15));
    WarSiege::Start(S,6,EWarSiegeScenario::LowerCity);
    TestEqual(TEXT("Rematch clears ownership"),WarSiege::ClaimedObjectives(S),uint16(0));
    S.Phase=EWarSiegePhase::Waiting;S.MilestoneSeconds.Add(1);
    TestEqual(TEXT("Lobby never displays stale ownership"),WarSiege::ClaimedObjectives(S),uint16(0));
    S.Phase=EWarSiegePhase::Active;S.OptionalClaims=5;
    TestEqual(TEXT("Optional claims survive stage transitions"),WarSiege::ClaimedObjectives(S),uint16(1281));
    S={};WarSiege::Start(S,6);P={};P.OptionalAttackers=6;
    WarSiege::Tick(S,P,45);
    TestEqual(TEXT("Completing sabotage claims its standard"),WarSiege::ClaimedObjectives(S),uint16(256));
    S.Stage=1;S.bOptionalComplete=false;S.OptionalProgress=0;
    WarSiege::Tick(S,P,45);
    TestEqual(TEXT("A later optional claim preserves the earlier standard"),WarSiege::ClaimedObjectives(S),uint16(768));
    UWarSiegeEquipmentDefinition* Definition=NewObject<UWarSiegeEquipmentDefinition>();FString Error;
    TestFalse(TEXT("Missing or unreviewed engine cannot spawn a fallback"),Definition->Validate(Error));
    const TArray<FVector> Trail{FVector::ZeroVector,FVector(1000,0,0),FVector(1000,1000,500)};
    TestTrue(TEXT("Following an incline interpolates the travelled ground height"),
        WarSiegeEquipment::TrailingPoint(Trail,850).Equals(FVector(1000,150,75),.001));
    TestTrue(TEXT("The support engine follows the corner instead of cutting through it"),
        WarSiegeEquipment::TrailingPoint(Trail,1300).Equals(FVector(700,0,0),.001));
    TestTrue(TEXT("The initial convoy spacing extends behind its spawn heading"),
        WarSiegeEquipment::TrailingPoint(Trail,2300).Equals(FVector(-300,0,0),.001));
    for (const FVector& Grades:{FVector(0,0,0),FVector(.6,.2,0),FVector(-.4,-.3,0)})
    {
        const FRotator Pose=WarSiegeEquipment::SurfaceRotation(37,Grades.X,Grades.Y);
        TestEqual(TEXT("Cross slope never changes the steering heading"),Pose.Yaw,37.);
        for (const FVector& Corner:{FVector(245,178,0),FVector(245,-178,0),FVector(-245,178,0),FVector(-245,-178,0)})
        {
            const FVector Aligned=FRotator(0,-37,0).RotateVector(Pose.RotateVector(Corner));
            TestTrue(TEXT("All four support points lie on the ground plane"),
                FMath::IsNearlyEqual(Aligned.Z,Grades.X*Aligned.X+Grades.Y*Aligned.Y,.001));
        }
    }
    return true;
}
#endif
